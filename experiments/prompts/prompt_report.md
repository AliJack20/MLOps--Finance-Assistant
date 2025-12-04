# Prompt Engineering Report

## Zero Shot

**Prompt:**
```
System: What is the difference between a stock and a bond?
```

**Response:**
```
Assistant: A stock represents ownership in a company, while a bond represents debt owed by an investor to a lender or issuer.
```

## Few Shot

**Prompt:**
```
System: You are a helpful financial assistant. Provide accurate and concise answers to financial questions. Here are some examples:

User: What is ROI?
Assistant: Return on Investment (ROI) is a performance measure used to evaluate the efficiency of an investment. It is calculated as (Current Value of Investment - Cost of Investment) / Cost of Investment.

User: What is a bull market?
Assistant: A bull market is a financial market of a group of securities in which prices are rising or are expected to rise. The term is most often used to refer to the stock market but can be applied to anything that is traded, such as bonds, real estate, currencies, and commodities.

User: What is a mutual fund?
Assistant: A mutual fund is a type of financial vehicle made up of a pool of money collected from many investors to invest in securities like stocks, bonds, money market instruments, and other assets. Mutual funds are operated by professional money managers, who allocate the fund's assets and attempt to produce capital gains or income for the fund's investors.

User: What is insider trading?
```

**Response:**
```
Assistant: Insider trading refers to the practice of using non-public information about a company's business operations, financial condition, or prospects to trade its shares before they become public knowledge. This activity is illegal because it creates an unfair advantage for those who engage in it, potentially harming other investors.
```

## Chain of Thought

**Prompt:**
```
System: You are a helpful financial assistant. Your task is to provide a detailed, step-by-step explanation before giving the final answer. Break down your reasoning process to ensure clarity and accuracy.

User: Should I invest in a high-risk stock for short-term gains?
Assistant: Let's think step by step.
```

**Response:**
```
Certainly! Before making any investment decisions, it's crucial to carefully consider several factors to determine if investing in a high-risk stock for short-term gains is appropriate for you. Here’s a detailed breakdown of the steps:

### 1. **Assess Your Investment Goals**
   - **Short-Term vs Long-Term:** Determine whether you need this money for an immediate purchase or want to hold onto it for a longer period (e.g., 3-5 years). Short-term investments typically offer higher potential returns but also come with greater risk.
   - **Risk Tolerance:** Consider how comfortable you are with taking on risk. High-risk stocks can lead to significant gains quickly, which might be appealing, but they also carry substantial volatility.

### 2. **Understand the Risks Involved**
   - **Market Volatility:** Understand that the stock market is inherently volatile. Even well-performing stocks can experience sudden drops due to various economic or geopolitical events.
   - **Company Specific**
```