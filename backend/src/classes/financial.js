class FinancialRecord {
  constructor(title,amount, type, date,category = new Date()) {
    this.title = title;
    this.amount = amount;
    this.type= type;
    this.date = date;
    this.category = category;
  }
}
module.exports = FinancialRecord;