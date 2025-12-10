const axios = require("axios");

// Ensure this matches your running Python port (usually 8000)
const PYTHON_API = process.env.AI_API_URL || "http://127.0.0.1:8000";

// 1. Call /classify
exports.classifyIntent = async (text) => {
  try {
    const response = await axios.post(`${PYTHON_API}/classify`, { text });
    return response.data; // Returns { intent: "...", filters: {...} }
  } catch (err) {
    console.error("❌ AI Classify Error:", err.message);
    return { intent: "chat" }; // Fallback to safe mode
  }
};

// 2. Call /extract
exports.extractData = async (text) => {
  try {
    const response = await axios.post(`${PYTHON_API}/extract`, { text });
    return response.data; // Returns array of transactions
  } catch (err) {
    console.error("❌ AI Extract Error:", err.message);
    return [];
  }
};

// 3. Call /answer
exports.generateAnswer = async (text, data = null) => {
  try {
    const response = await axios.post(`${PYTHON_API}/answer`, { text, data });
    return response.data.response; // Returns friendly text string
  } catch (err) {
    console.error("❌ AI Answer Error:", err.message);
    return "I'm having trouble connecting to my brain right now.";
  }
};