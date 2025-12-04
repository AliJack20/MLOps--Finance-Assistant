const express = require("express");
const bodyParser = require("body-parser");
const userRoutes = require("./routes/user.routes");
const financialRoutes = require("./routes/financial.routes");
const chatRoutes = require("./routes/chat.routes");
const cors = require("cors");

const app = express();
app.use(bodyParser.json());
const auth = require("./middleware/auth");
app.use(cors({
  origin: "http://localhost:4200",   // your Angular app URL
  credentials: true                  // allow cookies / auth headers if needed
}));// Routes
app.use("/users", userRoutes);
app.use("/financial", auth,financialRoutes);
app.use("/chat",auth ,chatRoutes);
module.exports = app;
