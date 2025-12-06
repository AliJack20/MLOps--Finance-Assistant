const mongoose = require("mongoose"); // <--- REQUIRED for ObjectId casting
const Financial = require("../models/financial.model");
const mlService = require("../services/ml.service");

exports.getDashboardStats = async (req, res) => {
  try {
    const userId = req.params.userId;
    const now = new Date();
    // First day of current month
    const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    // 1. Calculate Totals (Income vs Expense) - The efficient DB way
    const totalStats = await Financial.aggregate([
      { $match: { user: new mongoose.Types.ObjectId(userId) } },
      { $group: { 
          _id: "$type", 
          total: { $sum: "$amount" } 
      }}
    ]);

    // Convert the array [{_id: 'income', total: 500}, ...] into a simple object
    const totals = { income: 0, expense: 0 };
    totalStats.forEach(stat => {
      if (stat._id === "income") totals.income = stat.total;
      if (stat._id === "expense") totals.expense = stat.total;
    });

    // 2. Calculate Monthly Stats
    const monthlyStats = await Financial.aggregate([
      { $match: { 
          user: new mongoose.Types.ObjectId(userId),
          date: { $gte: firstDayOfMonth }
      }},
      { $group: { 
          _id: "$type", 
          total: { $sum: "$amount" } 
      }}
    ]);

    const monthlyTotals = { income: 0, expense: 0 };
    monthlyStats.forEach(stat => {
      if (stat._id === "income") monthlyTotals.income = stat.total;
      if (stat._id === "expense") monthlyTotals.expense = stat.total;
    });

    // 3. Category Breakdown (For Doughnut Chart)
    const categoryStats = await Financial.aggregate([
      { $match: { user: new mongoose.Types.ObjectId(userId), type: "expense" } },
      { $group: { 
          _id: "$category", 
          total: { $sum: "$amount" },
          color: { $first: "$color" } // Keeps the color consistent
      }},
      { $sort: { total: -1 } } // Sort highest expenses first
    ]);

    // 4. Get Recent Transactions
    const recentTransactions = await Financial.find({ user: userId })
      .sort({ date: -1 })
      .limit(5);

    // 5. Get ML Prediction
    const prediction = await mlService.getWeeklyPrediction(userId);

    // const prediction = {
    //   prediction_next_week: 250, // The value you want to show
    //   input: null
    // };
    
    // Send final response
    res.json({
      balance: totals.income - totals.expense,
      monthlyIncome: monthlyTotals.income,
      monthlyExpense: monthlyTotals.expense,
      categoryStats,       // Usage: Chart.js data source
      recentTransactions,  // Usage: Recent Activity list
      prediction           // Usage: "Predicted Spend" widget
    });

  } catch (err) {
    console.error("Dashboard Error:", err);
    res.status(500).json({ error: err.message });
  }
};