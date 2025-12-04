const axios = require("axios");
const Financial = require("../models/financial.model");
const mongoose = require("mongoose");

exports.getWeeklyPrediction = async (userId) => {
  try {
    // 1. Calculate the start of the current week (assuming Monday start)
    const today = new Date();
    const day = today.getDay(); // 0 (Sun) to 6 (Sat)
    const diff = today.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
    
    const startOfWeek = new Date(today.setDate(diff));
    startOfWeek.setHours(0, 0, 0, 0);

    // 2. Aggregate TOTAL spending for this current week so far
    const currentWeekStats = await Financial.aggregate([
      { 
        $match: { 
          user: new mongoose.Types.ObjectId(userId),
          type: "expense",
          date: { $gte: startOfWeek } 
        } 
      },
      { 
        $group: { 
          _id: null, 
          totalSpending: { $sum: "$amount" } 
        } 
      }
    ]);

    const currentSpending = currentWeekStats.length > 0 ? currentWeekStats[0].totalSpending : 0;

    // 3. Prepare payload EXACTLY as Python api.py expects it
    // Format date as MM/DD/YYYY or whatever your model trained on. 
    // Your comment said "04/01/2004", which is usually MM/DD/YYYY in US or DD/MM/YYYY elsewhere.
    // I'll use ISO format YYYY-MM-DD to be safe, or match your specific training format.
    const dateString = startOfWeek.toISOString().split('T')[0]; 

    const payload = {
      week: dateString,
      actual_spending: currentSpending
    };

    // 4. Call Python API
    const pythonUrl = process.env.PYTHON_ML_API_URL || "http://127.0.0.1:8000/predict";
    
    // Note: Your Python code does: df = pd.DataFrame([payload])
    // So we send the object directly.
    const response = await axios.post(pythonUrl, payload);
    
    // 5. Return the result
    // Python returns: { "prediction_next_week": 123.45, "input": ... }
    return response.data; 

  } catch (err) {
    console.error("ML Service Error:", err.message);
    // Return null so the dashboard doesn't crash if ML is down
    return null; 
  }
};