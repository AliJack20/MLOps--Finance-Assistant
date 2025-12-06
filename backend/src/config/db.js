const mongoose = require("mongoose");

const connectDB = async () => {
  try {
    // REMOVED: { useNewUrlParser: true, useUnifiedTopology: true }
    // Mongoose 6+ does this automatically now.
    await mongoose.connect(process.env.MONGODB_URI);
    
    console.log("✅ MongoDB Connected Successfully");
  } catch (err) {
    console.error("❌ MongoDB Connection Error:", err.message);
    process.exit(1); // Exit if DB fails
  }
};

module.exports = connectDB;