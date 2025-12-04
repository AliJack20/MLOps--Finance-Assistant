require("dotenv").config();
const connectDB = require("./config/db");
const app = require("./app");
const cors = require("cors");

// Connect DB
connectDB();
//whatsApp.start();
// Start reminder cron job
//startFinancialReminderWorker();


// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
