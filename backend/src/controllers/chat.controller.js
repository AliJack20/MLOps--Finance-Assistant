const Financial = require("../models/financial.model");
const aiService = require("../services/ai.service");


const buildDateQuery = (timeRange) => {
  if (!timeRange) return {};

  const now = new Date();
  const currentYear = now.getFullYear();
  const text = timeRange.toLowerCase().trim();

  // --- 🔥 NEW: DYNAMIC NUMBER PARSER ---
  // Matches: "last 6 months", "past 30 days", "last 2 years"
  // Regex explains: 
  //   (last|past) -> Ignore prefix
  //   (\d+)       -> Capture the Number (e.g., 6)
  //   (day|week|month|year) -> Capture the Unit
  const dynamicMatch = text.match(/(?:last|past)\s+(\d+)\s+(day|week|month|year)s?/);
  
  if (dynamicMatch) {
    const number = parseInt(dynamicMatch[1]); // e.g., 6
    const unit = dynamicMatch[2];             // e.g., "month"
    
    const startDate = new Date(now);
    
    // Perform precise math based on unit
    if (unit === 'day') startDate.setDate(now.getDate() - number);
    if (unit === 'week') startDate.setDate(now.getDate() - (number * 7));
    if (unit === 'month') startDate.setMonth(now.getMonth() - number);
    if (unit === 'year') startDate.setFullYear(now.getFullYear() - number);
    
    // Set to start of that day
    startDate.setHours(0, 0, 0, 0);
    
    return { $gte: startDate };
  }

  // --- EXISTING LOGIC (Specific years/ranges) ---
  
  // 1. "2023 - 2025"
  const rangeMatch = text.match(/^(\d{4})\s*-\s*(\d{4})$/);
  if (rangeMatch) {
    return {
      $gte: new Date(parseInt(rangeMatch[1]), 0, 1),
      $lte: new Date(parseInt(rangeMatch[2]), 11, 31, 23, 59, 59)
    };
  }

  // 2. "2024" (Specific Year)
  const yearMatch = text.match(/^(\d{4})$/);
  if (yearMatch) {
    return {
      $gte: new Date(parseInt(yearMatch[1]), 0, 1),
      $lte: new Date(parseInt(yearMatch[1]), 11, 31, 23, 59, 59)
    };
  }

  // 3. "This Month" / "This Week" (Current relative)
  if (text.includes("this month")) {
    return { $gte: new Date(currentYear, now.getMonth(), 1) };
  }
  if (text.includes("this week")) {
    const day = now.getDay() || 7; 
    if (day !== 1) now.setHours(-24 * (day - 1)); 
    now.setHours(0,0,0,0);
    return { $gte: now };
  }
  if (text.includes("this year")) {
    return { $gte: new Date(currentYear, 0, 1) };
  }

  return {}; 
};
exports.handleChat = async (req, res) => {
  try {
    const { message } = req.body;
    const userId = req.user._id;
    if (!message) return res.status(400).json({ error: "Message is required" });

    // 🧠 STEP 1: Ask Python "What does the user want?"
    const intentObj = await aiService.classifyIntent(message);
    console.log("🤖 Intent Detected:", intentObj);

    // ============================
    // 🟢 CASE 1: CREATE / BULK ADD
    // ============================
    if (intentObj.intent === "create") {
      // 1. Ask Python to extract structured data
      const extractedData = await aiService.extractData(message);

      if (!extractedData || extractedData.length === 0) {
        return res.json({ 
          response: "I understood you want to add a transaction, but I couldn't capture the details. Try saying 'Spent 50 on Food'." 
        });
      }

      // 2. Prepare data for MongoDB
      const transactionsToInsert = extractedData.map(item => ({
        user: userId,
        title: item.title || "Unknown Transaction",
        amount:Math.abs(item.amount),
        type: item.type || 'expense',
        category: item.category || "General",
        date: new Date(), 
        color: item.type === 'income' ? '#22c55e' : '#ef4444' // Default colors
      }));

      // 3. Save to Database
      await Financial.insertMany(transactionsToInsert);

      return res.json({ 
        response: `✅ I've added ${transactionsToInsert.length} new transaction(s) for you.`,
        created:true
      });
    }

    // ============================
    // 🟡 CASE 2: QUERY DATA
    // ============================
    if (intentObj.intent === "query") {
      const filters = intentObj.filters || {};
      const query = { user: userId };

      // A. Category Filter (Simple Regex)
      // A. Category Filter (Ignore 'All')
      if (filters.category && filters.category.toLowerCase() !== 'all') {
        query.category = { $regex: filters.category, $options: "i" };
      }

      // B. 🔥 NEW ROBUST DATE LOGIC
      if (filters.time_range) {
        const dateQuery = buildDateQuery(filters.time_range);
        if (Object.keys(dateQuery).length > 0) {
          query.date = dateQuery;
        }
      }
      // C. Type Filter (if LLM detects 'income' vs 'expense' specifically)
      if (filters.type) {
        query.type = filters.type.toLowerCase();
      }
      console.log("🔍 Mongo Query:", JSON.stringify(query, null, 2)); // Debugging
      // 1. Fetch from Database
      // Limit to 20 to prevent overwhelming the LLM prompt context
      const records = await Financial.find(query).sort({ date: -1 }).limit(20);
      console.log("📊 Records Found:", records);
      // 2. Ask Python to summarize these records
      const summary = await aiService.generateAnswer(message, records);
      console.log("🧾 Summary Generated:", summary);
      return res.json({ response: summary });
    }

    // ============================
    // 🔵 CASE 3: GENERAL CHAT
    // ============================
    // No DB action needed, just talk
    const chatReply = await aiService.generateAnswer(message, null);
    return res.json({ response: chatReply });

  } catch (err) {
    console.error("Chat Controller Error:", err);
    res.status(500).json({ error: "Something went wrong processing your request." });
  }
};