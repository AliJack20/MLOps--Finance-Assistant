const Financial = require("../models/financial.model");
const User = require("../models/user.model");
const mongoose = require("mongoose");

// --- HELPER: Strict Category Validation ---
const isCategoryAllowed = (category) => {
  if (!category) return false;
  const lower = category.trim().toLowerCase();
  return lower !== "income" && lower !== "expense";
};

// 1. BULK ADD (Secure)
exports.BulkaddFinancial = async (req, res) => {
  try {
    // ✅ SECURE: Get ID from Token, not body
    const userId = req.user._id; 

    if (!Array.isArray(req.body.financials) || req.body.financials.length === 0) {
      return res.status(400).json({ error: "No financial entries provided" });
    }

    for (const item of req.body.financials) {
      if (!isCategoryAllowed(item.category)) {
        return res.status(400).json({ 
          error: `Restricted Category detected: '${item.category}'. Please use specific names like 'Salary' or 'Rent'.` 
        });
      }
    }

    const financialsToInsert = req.body.financials.map(financial => ({
      user: userId, // ✅ Force the logged-in user
      title: financial.title,
      amount: financial.amount,
      type: financial.type,
      date: financial.date,
      category: financial.category,
      color: financial.color
    }));

    const insertedFinancials = await Financial.insertMany(financialsToInsert, { ordered: false });
    
    return res.status(201).json({
      message: "All Records Inserted Successfully",
      financials: insertedFinancials
    });
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
};

// 2. ADD SINGLE (Secure)
exports.addFinancial = async (req, res) => {
  try {
    // ✅ SECURE: Ignore 'user' from body
    const { title, amount, type, date, category, color } = req.body;
    const userId = req.user._id; 

    if (!isCategoryAllowed(category)) {
      return res.status(400).json({ 
        error: "Category cannot be 'Income' or 'Expense'. Please use a specific name." 
      });
    }

    const financial = await Financial.create({
      user: userId, // ✅ Force logged-in user
      title,
      amount,
      type,
      date,
      category,
      color
    });

    res.status(201).json(financial);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

// 3. GET ALL (Secure)
exports.getFinancials = async (req, res) => {
  try {
    // ✅ SECURE: Ignore params.userId, use token
    const financials = await Financial.find({ user: req.user._id }).sort({ date: -1 }).lean();
    
    let income = 0;
    let expenses = 0;

    financials.forEach(entry => {
      if (entry.type === "income") {
        income += entry.amount || 0;
      } else if (entry.type === "expense") {
        expenses += entry.amount || 0;
      }
    });

    res.json({
      financials,
      income,
      expenses,
      savings: income - expenses
    });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

// 4. GET BY ID (Secure)
exports.getFinancialById = async (req, res) => {
  try {
    const { financialId } = req.params;
    // ✅ SECURE: Must match Record ID AND User ID
    const financial = await Financial.findOne({ _id: financialId, user: req.user._id });
    
    if (!financial) return res.status(404).json({ error: "Financial entry not found" });
    res.json(financial);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

// 5. UPDATE (Secure)
exports.updateFinancial = async (req, res) => {
  try {
    const { financialId } = req.params;
    
    // ✅ SECURE: Strip malicious fields manually or just destructure safe ones
    // We remove _id and user from the update object just in case
    const { _id, user, ...updateData } = req.body; 

    if (req.body.category && !isCategoryAllowed(req.body.category)) {
      return res.status(400).json({ 
        error: "Category cannot be 'Income' or 'Expense'. Please use a specific name." 
      });
    }

    const financial = await Financial.findOneAndUpdate(
      { _id: financialId, user: req.user._id }, // ✅ Query must include user ID
      updateData,
      { new: true, runValidators: true }
    );

    if (!financial) return res.status(404).json({ error: "Financial entry not found" });
    res.json(financial);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

// 6. DELETE (Secure)
exports.deleteFinancial = async (req, res) => {
  try {
    const { financialId } = req.params;
    
    // ✅ SECURE: Must match Record ID AND User ID
    const financial = await Financial.findOneAndDelete({ _id: financialId, user: req.user._id });
    if (!financial) return res.status(404).json({ error: "Financial entry not found" });
    
    res.json({ message: "Financial entry deleted successfully" });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

// 7. GET FILTERS (Secure)
exports.getTransactionFilters = async (req, res) => {
  try {
    // ✅ SECURE: Use ID from token
    const userId = req.user._id; 
    
    // Mongoose aggregation requires ObjectId type
    // req.user._id is already an ObjectId usually, but good to be safe if it's a string
    const userObjectId = new mongoose.Types.ObjectId(userId); 

    const categories = await Financial.distinct("category", { user: userId });

    const yearsData = await Financial.aggregate([
      { $match: { user: userObjectId } },
      { 
        $project: { 
          year: { $year: "$date" } 
        } 
      },
      { 
        $group: { 
          _id: "$year" 
        } 
      },
      { $sort: { _id: -1 } }
    ]);

    const years = yearsData.map(y => y._id.toString());

    res.json({
      categories: categories.sort(), 
      years: years
    });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};