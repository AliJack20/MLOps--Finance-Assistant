const express = require("express");
const { handleChat } = require("../controllers/chat.controller");
// Assuming you have auth middleware to protect this route
// const auth = require("../middleware/auth"); 

const router = express.Router();

// POST http://localhost:3000/chat/ask
router.post("/ask", handleChat);

module.exports = router;