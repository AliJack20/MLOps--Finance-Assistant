const mongoose = require("mongoose");

const financialSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  title: { type: String, required: true },
  amount: { type: Number, required: true, min: 0 },
  
  // "Income" or "Expense"
  type: { type: String, enum: ["income", "expense"], required: true },
  
  date: { type: Date, default: Date.now },
  
  // Category Name (e.g., "Food")
  category: { type: String, required: true },
  
  color: { type: String, default: "#3f51b5" }, 

  createdAt: { type: Date, default: Date.now },
});

module.exports = mongoose.model("Financial", financialSchema);