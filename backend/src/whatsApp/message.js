// const { Client, LocalAuth } = require('whatsapp-web.js');
// const qrcode = require('qrcode');
// const fs = require('fs');
// const User = require("../models/user.model");
// const axios = require("axios"); // to call backend API
// const FinancialRecord = require("../classes/financial");
// const { parse } = require('path');
// const conversations = {}; // memory of user flows
// const baseFinancialUrl = "http://localhost:3000/financial"; // adjust as needed
// const client = new Client({
//         authStrategy: new LocalAuth(),  // Saves session automatically
//         puppeteer: { headless: true }
//     });
// async function start()
//     {
    

//     client.on('qr', async (qr) => {
//         console.log('Scan the QR code below:');
        
//         // Show QR in terminal
//         const qrcodeTerminal = await import('qrcode-terminal');
//         qrcodeTerminal.default.generate(qr, { small: true });

//         // Save QR as PNG locally
//         const qrImagePath = './whatsapp_qr.png';
//         qrcode.toFile(qrImagePath, qr, { width: 300 }, (err) => {
//             if (err) console.error('Error saving QR:', err);
//             else console.log(`✅ QR code saved at ${qrImagePath}`);
//         });
//     });

//     client.on('ready', () => {
//         console.log('✅ WhatsApp is ready!');
//     });

//     client.initialize();

//     client.on("message", async (msg) => {
//     const phone = msg.from;
//     const cleanPhone = phone.replace("@c.us", "");
//     const text = msg.body.trim().toLowerCase();

//     const user = await User.findOne({ phone: cleanPhone });
//     if (!user) return msg.reply("❌ Please register first.");
//     if(text==="create" || (conversations[cleanPhone] && conversations[cleanPhone].command=='create')) return CreateRecord(text,cleanPhone,msg,user);
//     else if (text === "report") return GetReport(msg, user);
//     if (text === "show") return ShowAllRecords(msg, user);
    
//     //above this all tested

//     else if (text==="delete" || (conversations[cleanPhone] && conversations[cleanPhone].command=='delete')) {
//      DeleteRecord(text,msg,cleanPhone,msg,user);
//      return;
//     }
//     else if (text==="edit"  || (conversations[cleanPhone] && conversations[cleanPhone].command=='edit')) {
//       EditRecord(text,msg,cleanPhone,msg,user);
//     }
//     else if (text==="bulk" || (conversations[cleanPhone] && conversations[cleanPhone].command=='bulk')) return BulkCreateRecord(text,cleanPhone,msg,user);

//     else if (text === "menu") return Menu(msg);
//     else
//       return msg.reply("❓ Unknown command. Type 'menu' for options.");
//   });
// }
// async function sendWhatsAppReminder(number, name) {
 
//   const chatId = `${number}@c.us`;

//   const message = `Hello ${name}, this is your financial reminder! Don't forget to review your finances today. 📊💰`;

//   try {
//     await client.sendMessage(chatId, message);
//     console.log(`📩 Reminder sent to ${name} (${chatId})`);
//   } catch (err) {
//     console.error("❌ Failed to send message:", err);
//   }
// }

// async function CreateRecord(text,phone,msg,user) 
// {

    
//   // 🚀 Start flow if user types "create"
//   if (text === "create" && !conversations[phone]) {
//     conversations[phone] = { command:"create",step: "type", data: {}, errors: 0 };
//     return msg.reply("Creating a new financial record!\n\nEnter the type:\n1. income\n2. expense");
//   }

//   // 📝 If user is not in conversation, ignore
//   if (!conversations[phone]) return;

//   const state = conversations[phone];

//   // --- Step 1: Type ---
//   if (state.step === "type") {
//     if (text === "1" || text.includes("income")) {
//       state.data.type = "income";
//       state.step = "amount";
//       return msg.reply("Please enter the amount:");
//     } else if (text === "2" || text.includes("expense")) {
//       state.data.type = "expense";
//       state.step = "amount";
//       return msg.reply("Please enter the amount:");
//     } else {
//       state.errors++;
//       if (state.errors >= 5) {
//         delete conversations[phone];
//         return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//       }
//       return msg.reply("❌ Invalid. Reply with 1 (income) or 2 (expense).");
//     }
//   }

//   // --- Step 2: Amount ---
//   if (state.step === "amount") {
//     const amount = parseFloat(text);
//     if (isNaN(amount)) {
//       state.errors++;
//       if (state.errors >= 5) {
//         delete conversations[phone];
//         return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//       }
//       return msg.reply("❌ Please enter a valid number for the amount.");
//     }
//     state.data.amount = amount;
//     state.step = "reason";
//     return msg.reply("Got it ✅ Now enter the reason:");
//   }

//   // --- Step 3: Reason ---
//   if (state.step === "reason") {
//     state.data.reason = msg.body; // keep raw text
//     try {
//       // ⚡ Call backend API (replace <USER_ID> mapping from phone → userId)
//       await axios.post(baseFinancialUrl+"/addfinancials", {
//         user: user._id, // TODO: map phone to actual user
//         amount: state.data.amount ,
//         kind: state.data.type === "expense" ? "expense" :"income",
//         reason: state.data.reason,
//         date: new Date()
//       });

//       msg.reply(`✅ ${state.data.type} of ${state.data.amount} added for: ${state.data.reason}`);
//     } catch (err) {
//       console.error("Error saving financial record:", err);
//       msg.reply("❌ Something went wrong saving your financial record.");
//     }

//     // ✅ Clear conversation (finished)
//     delete conversations[phone];
    
//   }
//   const response = await axios.get(`${baseFinancialUrl}/GetAllfinancials/${user._id}`);
//     const financials = response.data; // this is JSON array
//     const message=`📊 Current Summary:\n` +
//       `Income: ${financials.income}\n` +
//       `Expenses: ${financials.expenses}\n` +
//       `Savings: ${financials.savings}\n\n` ;
//     msg.reply(message);

//   delete conversations[phone]; // clear state
    
    
// }
// async function sendMessage(chatId, message) 
// {
//     try {
//     await client.sendMessage(chatId, message);
   
//   } catch (err) {
//     console.error("❌ Failed to send message:", err);
//   }
// }
// module.exports = { start, sendWhatsAppReminder,CreateRecord, sendMessage };

// // inside whatsapp.js


// // need to fix 
// async function GetReport(msg, user) {
//   try {
//     const response = await axios.get(`${baseFinancialUrl}/GetAllfinancials/${user._id}`);
//     const financials = response.data;
//     console.log(financials);
//     await msg.reply(
//       `📊 Financial Report for ${user.name}\n\n` +
//       `Income: ${financials.income}\nExpenses: ${financials.expenses}\nSavings: ${financials.savings}`
//     );
//   } catch (err) {
//     console.error(err);
//     await msg.reply("❌ Could not fetch financial report.");
//   }
// }

// async function ShowAllRecords(msg, user) {
//   try {
//     const response = await axios.get(`${baseFinancialUrl}/GetAllfinancials/${user._id}`);
//     const data = response.data;
//     const financials = data.financials;

//     if (financials.length === 0) return msg.reply("📭 No records found.");

//     let message = "📋 Your Records:\n\n";
//     financials.forEach((f, i) => {
//       message += `${i + 1}. [${f._id}]\n`;
//       message += `   Type: ${f.kind > 0 ? "Income" : "Expense"}\n`;
//       message += `   Amount: ${f.amount}\n`;
//       message += `   Reason: ${f.reason}\n`;
//       message += `   Date: ${new Date(f.date).toLocaleDateString()}\n\n`;
//     });
//     message+='Total Income: ' + data.income + '\n' +
//              'Total Expenses: ' + data.expenses + '\n' +
//              'Total Savings: ' + data.savings + '\n';

//     await msg.reply(message);
//     return financials;
//   } catch (err) {
//     console.error(err);
//     await msg.reply("❌ Could not fetch records.");
//   }
// }

// async function DeleteRecord(text,msg,phone,msg,user) {
//   try {
//     if(!conversations[phone])
//     {
//       try{
//         const record =await ShowAllRecords(msg,user);
//         conversations[phone] = { command:"delete",step: "id", id:0, errors: 0,record:record };
//         return msg.reply("Please reply with the ID of the record you want to delete, prefixed by 'delete'. For example: delete 12345");
//       }
//       catch(err)
//       {
//         console.error(err);
//       }
//     }
//     const state = conversations[phone];

//     // Step 1: Waiting for ID
//     const newText=text.split(" ")
//     if (newText[0] === "delete" || (conversations[phone] && conversations[phone].step=='id')) 
//     {
//       var index=null;
//       if (newText.length ==1) {
//         index= parseInt(text, 10);
//       }
//       else{
//         index = parseInt(newText[1], 10); // Convert to integer
//       }
//       if (isNaN(index) || index < 0 || index >= state.record.length) {
//         return msg.reply("❌ Invalid record ID. Please provide a valid number.");
//       }
//       state.step="confirm";
//       state.id = state.record[index-1]._id; // Safely access the record
//       const selectedRecord = state.record[index-1];
//       return msg.reply(`Are you sure you want to change the amount to ${state.newAmount} for record \n Kind: ${selectedRecord.kind} \n Amount: ${selectedRecord.amount} \n Reason:${selectedRecord.reason} ? Reply with 'yes' to confirm or 'no' to cancel.`);
//     }  

//     // Step 2: Confirmation
//     if (state.step === "confirm") {
//       if (text === "yes") 
//       {
//         try {
//           await axios.delete(`${baseFinancialUrl}/${user._id}/Deletefinancials/${state.id}`);
//           msg.reply(`🗑️ Record ${state.id} deleted successfully.`);
//         } catch (err) {
//           console.error(err);
//           msg.reply("❌ Could not delete record. Check the ID.");
//         }
//         delete conversations[phone];
//         return;
//       } else if (text === "no")
//       {
//         msg.reply("❌ Deletion cancelled.");
//         delete conversations[phone];
//         return;
//       }
//       else 
//         {
//           state.errors++;
//           if (state.errors >= 5) 
//             {
//             delete conversations[phone];
//             return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//           }
//           return msg.reply("❌ Invalid. Reply with yes or no.");
//         }
//     }
//   } catch (err) {
//     console.error(err);
//     await msg.reply("❌ Could not process deletion.");
//   }
// }

// async function EditRecord(text,msg,phone,msg,user) {
//   try {
//     if(!conversations[phone]){
//       try{
//         const record =await ShowAllRecords(msg,user);
//         conversations[phone] = { command:"edit",step: "id", id:null, errors: 0,editType:null,newAmount:-1,kind:null,reason:null,record:record };
//         return msg.reply("Please reply with the ID of the record you want to edit, prefixed by 'edit'. For example: edit 12345");
        
//       }
//       catch(err)
//       {
//         console.error(err);
//       }
//     }
    
//     const state = conversations[phone];
//     const newText=text.split(" ")
//     if (newText[0] === "edit" || (conversations[phone] && conversations[phone].step=='id')) 
//     {
//       var index=null;
//       if (newText.length ==1) {
//         index= parseInt(text, 10);
//       }
//       else{
//         index = parseInt(newText[1], 10); // Convert to integer
//       }
//       if (isNaN(index) || index < 0 || index >= state.record.length) {
//         return msg.reply("❌ Invalid record ID. Please provide a valid number.");
//       }
//       state.step="editFeature";
//       state.id = state.record[index-1]._id; // Safely access the record
//       return msg.reply("The edit Financial selected what would you like to change? \n\nEnter the type:\n1. Kind (Income or Expense) \n2. Reason \n3. Amount \n either enter the number or the word exactly as spelled here");
//     }
   

//     // Step 1: Waiting for ID
//     if (state.step === "editFeature") 
//     {
//       if (text === "1" || text==="kind") 
//       {
//         state.editType = "kind";
//         state.step = "enter";
//         return msg.reply("Please enter the Updated kind you want to make \n\nEnter the type:\n1. income\n2. expense");
//       } 
//       else if (text === "2" || text==="reason") 
//       {
//         state.editType = "reason";
//         state.step = "enter";
//         return msg.reply("Please enter the reason:");
//       } 
//       else if (text === "3" || text==="amount") 
//       {
//         state.editType = "amount";
//         state.step = "enter";
//         return msg.reply("Please enter the amount:");
//       } 
      
//       else 
//       {
//         state.errors++;
//         if (state.errors >= 5) {
//           delete conversations[phone];
//           return msg.reply("❌ Too many mistakes. Restart by typing 'edit'.");
//         }
//         return msg.reply("❌ Invalid. Reply with 1 (kind) or 2 (reason) or 3 (amount).");
//       }
//     }
    
//     if(state.step==="enter")
//     {
//       if(state.editType==="kind")
//       {
//         if (text === "1" || text.includes("income")) {
//           state.kind = "income";
//           state.step = "confirm";
//           const selectedRecord = state.record.find(r => r._id === state.id);
//           return msg.reply(`Are you sure you want to change the amount to ${state.newAmount} for record \n Kind: ${selectedRecord.kind} \n Amount: ${selectedRecord.amount} \n Reason:${selectedRecord.reason} ? Reply with 'yes' to confirm or 'no' to cancel.`);
//         }
//         else if (text === "2" || text.includes("expense")) {
//           state.kind = "expense";
//           state.step = "confirm";
//          const selectedRecord = state.record.find(r => r._id === state.id);
//           return msg.reply(`Are you sure you want to change the amount to ${state.newAmount} for record \n Kind: ${selectedRecord.kind} \n Amount: ${selectedRecord.amount} \n Reason:${selectedRecord.reason} ? Reply with 'yes' to confirm or 'no' to cancel.`);
//         }
//         else {
//           state.errors++;
//           if (state.errors >= 5) {
//             delete conversations[phone];
//             return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//           }
//           return msg.reply("❌ Invalid. Reply with 1 (income) or 2 (expense).");
//         }

//       }

//       else if(state.editType==="reason")
//       {
//         state.reason = msg.body;
//         state.step = "confirm";
//         const selectedRecord = state.record.find(r => r._id === state.id);
//         return msg.reply(`Are you sure you want to change the amount to ${state.newAmount} for record \n Kind: ${selectedRecord.kind} \n Amount: ${selectedRecord.amount} \n Reason:${selectedRecord.reason} ? Reply with 'yes' to confirm or 'no' to cancel.`);
//       }
//       else if(state.editType==="amount")
//       {
        
//         const sanitizedText = text.replace(/[^0-9.]/g, "");
//         const amount = parseFloat(sanitizedText);
//         if (isNaN(amount)) {
//           state.errors++;
//           if (state.errors >= 5) {
//             delete conversations[phone]; 
//             return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//           }
//           return msg.reply("❌ Please enter a valid number for the amount.");
//         }
//         state.newAmount = amount;
//         state.step = "confirm";
//         const selectedRecord = state.record.find(r => r._id === state.id);
//         return msg.reply(`Are you sure you want to change the amount to ${state.newAmount} for record \n Kind: ${selectedRecord.kind} \n Amount: ${selectedRecord.amount} \n Reason:${selectedRecord.reason} ? Reply with 'yes' to confirm or 'no' to cancel.`);
//       }
//      } 
 
  
//     if (state.step === "confirm") 
//     {
//       if (text === "yes") {
//         const payload = 
//       {
//         ...(state.kind=='income' || state.kind=='expense' ? { kind: state.kind } : {}),
//         ...(state.newAmount>0 ? { amount: state.newAmount } : {}),
//         ...(state.reason ? { reason: state.reason } : {})
//       };
//         try {
//           const newRecord=await axios.put(`${baseFinancialUrl}/${user._id}/Updatefinancials/${state.id}`,payload);
//           msg.reply(`🗑️ Record ${newRecord} updated successfully.`);
//         } catch (err) {
//           console.error(err);
//           msg.reply("❌ Could not update record. Check the ID.");
//         }
//         delete conversations[phone];
//         return;
//       } else if (text === "no") {
//         msg.reply("❌ Edit cancelled.");
//         delete conversations[phone];
//         return;
//       } 
//       else {
//          if (state.errors >= 5) {
//             delete conversations[phone]; 
//             return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//           }
//           return msg.reply("❌ Please enter a valid command 'yes' or 'no'.");
        
//       }
//     }
 
//   } catch (err) {
//     console.error(err);
//     await msg.reply("❌ Could not process edit.");
//   }
// }

// async function BulkCreateRecord(text,phone,msg,user) 
// {

    
//   // 🚀 Start flow if user types "create"
//   if (!conversations[phone]) {
//     conversations[phone] = { command:"bulk",step: "type", data: [], errors: 0 ,kind:null};
//     return msg.reply("Creating a Bulk of new financial record!\n\nEnter the type You want to Create in bulk:\n1. income\n2. expense");
//   }

//   // 📝 If user is not in conversation, ignore
//   if (!conversations[phone]) return;

//   const state = conversations[phone];

//   // --- Step 1: Type ---
//   if (state.step === "type") {
//     if (text === "1" || text.includes("income")) {
//       state.kind = "income";
//       state.step = "amount";
//       return msg.reply("Please enter the Message in the following format \n :"+
//         "Amount : Reason \n"+
//         "Each record on a new line.\nExample:\n1000 : Salary\n200 : Freelance Work\n50 : Gift"
//       );
//     } else if (text === "2" || text.includes("expense")) {
//       state.kind = "expense";
//       state.step = "creation";
//        return msg.reply("Please enter the Message in the following format \n :"+
//         "Amount : Reason \n"+
//         "Each record on a new line.\nExample:\n1000 : Salary\n200 : Freelance Work\n50 : Gift"
//       );
//     } else {
//       state.errors++;
//       if (state.errors >= 5) {
//         delete conversations[phone];
//         return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//       }
//       return msg.reply("❌ Invalid. Reply with 1 (income) or 2 (expense).");
//     }
//   }

//   // --- Step 2: Amount ---
//   if (state.step === "creation") {
//     const lines=text.split("\n");
    
//     for(const line of lines)
//     {
//       const parts=line.split(":"); 
//       const amount = parseFloat(parts[0]);
//       if(parts.length!=2 || isNaN(amount) )
//       {
//         state.errors++;
//         if (state.errors >= 5) {
//           delete conversations[phone];
//           return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//         }
//         return msg.reply("❌ Please enter a valid format for each line: Amount : Reason");
//       }
      
//       state.data.push(new FinancialRecord(amount,state.kind,parts[1].trim(),new Date()));
//     }
//     state.step="confirm"
//     return msg.reply(`Got it ✅ \n All These are the records you wanted right\n Enter 'yes' or 'no' \n${state.data} `);
//   }

//   // --- Step 3: Reason ---
//   if (state.step === "confirm") {
//     state.data.reason = msg.body; // keep raw text
//     try {
//       if(text=="yes")
//       {
//         //fix this and probably make a interface or class or something 
//         await axios.post
//         (baseFinancialUrl+"/BulkAddfinancials", 
//           {
//             user: user._id, // TODO: map phone to actual user
//             financials: state.data
//           }
//         );
//       }
//       else if (text === "no")
//       {
//         msg.reply("❌ Deletion cancelled.");
//         delete conversations[phone];
//         return;
//       }
//       else 
//       {
//         state.errors++;
//         if (state.errors >= 5) 
//           {
//           delete conversations[phone];
//           return msg.reply("❌ Too many mistakes. Restart by typing 'create'.");
//         }
//         return msg.reply("❌ Invalid. Reply with yes or no.");
//       } 
//     } catch (err) {
//       console.error("Error saving financial record:", err);
//       msg.reply("❌ Something went wrong saving your financial record.");
//     }

//     // ✅ Clear conversation (finished)
//     delete conversations[phone];
    
//   }
//   const response = await axios.get(`${baseFinancialUrl}/GetAllfinancials/${user._id}`);
//     const financials = response.data; // this is JSON array
//     const message=`📊 Current Summary:\n` +
//       `Income: ${financials.income}\n` +
//       `Expenses: ${financials.expenses}\n` +
//       `Savings: ${financials.savings}\n\n` ;
//     msg.reply(message);

//   delete conversations[phone]; // clear state
    
    
// }

// async function Menu(msg) {
//   await msg.reply(
//     "📌 Available Commands:\n\n" +
//     "➡️ create – Add a new financial record\n" +
//     "➡️ report – View summary (income, expenses, savings)\n" +
//     "➡️ show – Show all records\n" +
//     "➡️ delete <id> – Delete a record\n" +
//     "➡️ edit <id> <amount> – Edit a record amount\n" +
//     "➡️ menu – Show this help menu"
//   );
// }
