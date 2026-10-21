# Generated answers

## `improved`

### q01: Two Singapore companies are each 80% owned by the same Hong Kong-incorporated parent. Can one of them set its current-year losses against the other's profits?

Gold: 37B, GR:6.1, GR:6.3

Yes – the two Singapore‑incorporated companies can transfer the current‑year loss items of one to offset the other’s assessable income, provided the group‑relief conditions are met.

- Both must be Singapore‑incorporated and belong to the same group on the last day of the basis period [e-Tax Guide: Group Relief System, para 5.1; e-Tax Guide: Group Relief System, para 2.3].  
- “Same group” means a relevant holding company (here the Hong Kong parent) holds at least 75 % ordinary shareholding in each company on that date [e-Tax Guide: Group Relief System, para 6.5; e-Tax Guide: Group Relief System, Annex 2]. An 80 % holding satisfies this test.  
- The companies must have the same accounting year‑end [e-Tax Guide: Group Relief System, para 5.1; e-Tax Guide: Group Relief System, para 2.3].  
- Only unabsorbed capital allowances, trade losses and donations of the current YA can be transferred, and they are transferred in the statutory order (current‑year capital allowances → current‑year trade losses → current‑year donations) [e-Tax Guide: Group Relief System, para 11.2].  
- If the claimant’s assessable income is insufficient, any remaining loss items stay with the transferor for carry‑back or carry‑forward [e-Tax Guide: Group Relief System, para 12.2].  
- The CIT may deny the transfer if the arrangement is primarily for tax avoidance [e-Tax Guide: Group Relief System, para 15.2].

So, assuming the same year‑end and the 80 % shareholding throughout the basis period, one company may set its current‑year losses against the other’s profits under the group‑relief system.

*groq:openai/gpt-oss-120b; citation precision 0.00*

### q02: A subsidiary closes its books on 31 March but its sister company has a 31 December year end. Can unused capital allowances be passed from one to the other?

Gold: 37B, GR:9.1

No. Unused capital allowances (unabsorbed capital allowances) can be transferred only between group companies that share the same accounting year‑end. The transferor and the claimant must have identical year‑ends; a third group member may have a different year‑end, but it cannot be the claimant or transferor [e-Tax Guide: Group Relief System, para 9.2; e-Tax Guide: Group Relief System, para 9.1].  

Because the subsidiary (31 Mar) and its sister company (31 Dec) have different year‑ends, they do not satisfy the “same accounting year‑end” condition, so the capital allowances cannot be passed between them [e-Tax Guide: Group Relief System, Annex 4] (examples where loss items cannot be transferred due to different year‑ends).  

Thus, unless the two companies align their accounting year‑ends, unused capital allowances cannot be transferred from one to the other.

*groq:openai/gpt-oss-120b; citation precision 0.33*

### q03: A company filed its return showing a profit, but IRAS's assessment turned the result into a loss. How long does it have to file the form needed to pass that loss to a sister company?

Gold: 37B, GR:14.2

It must submit the required form within **2 months of the date of the notice of assessment**.  

- Because the company filed a return showing profit but the CIT’s assessment turned it into a loss, it becomes a “new transferor”. Under the group‑relief rules it must lodge **Form GR A** no later than 2 months after the assessment notice, and the sister company (claimant) must lodge **Form GR B** within the same 2‑month period. If either form is not filed within that time, the CIT will refuse the loss transfer [e-Tax Guide: Group Relief System, para 14.2].

*groq:openai/gpt-oss-120b; citation precision 1.00*

### q04: The profitable subsidiary wants to pay the loss-making subsidiary for the tax losses it absorbs. Can the payer deduct that payment, and is it taxable for the company receiving it?

Gold: GR:16.1

No. If the profitable subsidiary (the claimant) makes a compensatory payment to the loss‑making subsidiary (the transferor) for the right to claim its loss items under group relief, the payment is **not deductible** for the payer, and the receipt is **not taxable** for the payee [e-Tax Guide: Group Relief System, para 16.1].

*groq:openai/gpt-oss-120b; citation precision 1.00*

### q05: A new company makes its first sale in March 2024 and has a 31 December year end. How far back before 1 January 2024 can its revenue expenses still be deducted?

Gold: 14R, PC:4.2

The company’s “deemed date of commencement” is the first day of the accounting year in which it earned its first dollar of sales – 1 January 2024 (first sale in March 2024 falls in the FY 2024).  

Under section 14R, revenue expenses incurred **on or after the deemed date** and **up to 12 months before the deemed date** are deductible (“s14R expenses”) [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 4.2; e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 3.7; e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 2.2]. The enterprise‑development concession expressly allows a deduction for revenue expenses incurred **1 year prior** to the deemed date [e-Tax Guide: Date of Commencement of Business, para 3.4].  

Therefore, revenue expenses incurred from **1 January 2023 onward** (i.e., up to 12 months before 1 Jan 2024) can still be claimed as tax deductions. Expenses incurred earlier than 1 Jan 2023 are pre‑commencement expenses and are not deductible as revenue expenses [e-Tax Guide: Date of Commencement of Business, para 3.2; e-Tax Guide: Date of Commencement of Business, para 2.3].

*groq:openai/gpt-oss-120b; citation precision 0.17*

### q06: In its first year a company earns both normally taxed income and income taxed at a concessionary rate. How are its set-up costs from before trading began deducted when they cannot be traced to either income stream?

Gold: 14X, PC:6.1

- Because the expenses cannot be shown to be directly attributable to either the normal‑rate or the concessionary‑rate income, they are treated as “remaining” pre‑commencement expenses [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 7.1].  
- The remaining expenses are **apportioned** to the two income streams in proportion to each stream’s share of total income in the first YA [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 2.3; e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 6.1].  
- The apportioned amount is then deducted against the corresponding income stream (normal‑rate income and concessionary‑rate income) [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 6.1].  
- If the apportioned expenses exceed the income of a stream, the excess forms part of the company’s trade loss, which may be:  
  1. offset against other income in the same YA,  
  2. carried forward to future YAs,  
  3. transferred to a related company under group relief, or  
  4. carried back to the immediate preceding YA [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 6.5].  

Thus, untraceable set‑up costs are allocated on an income‑proportion basis and deducted accordingly; any surplus becomes a trade loss available for the relief options above.

*groq:openai/gpt-oss-120b; citation precision 0.25*

### q07: Can a company whose property investment business is taxed under section 10D deduct revenue expenses it incurred before it earned any rental income?

Gold: 14R

No. Because the company’s business falls under section 10D, revenue outgoings incurred before any rental income is earned are not deductible.  

- Section 10D(1)(a) expressly states that “any outgoings and expenses … in respect of investments … that do not produce any income are not allowed as a deduction under section 14” for that business [ITA 1947, s 10D(1)].  
- Section 14R(4) confirms that the pre‑commencement deduction regime of section 14R does not apply to a business of making investments to which section 10D applies [ITA 1947, s 14R(4)].  

Therefore, revenue expenses incurred prior to earning the first rental receipt cannot be claimed as a tax deduction. (The guides on S14N or pre‑commencement expenses do not override this rule.)

*groq:openai/gpt-oss-120b; citation precision 0.50*

### q08: A start-up's deductible expenses from before it opened are larger than the income it earns in its first year. What can it do with the unused amount?

Gold: PC:6.5

The excess pre‑commencement / s14R expenses become **trade losses**.  
You may:

- **Offset them against other income in the same YA** (e.g., other business or personal income) [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 6.5].  
- **Carry them forward** to deduct against taxable income in future YAs, provided you still satisfy the business test (and the share‑holding test if you are a company) [e-Tax Guide: Carry-back Relief System, para 6.6; e-Tax Guide: Renovation or Refurbishment Works, para 7.2].  
- **Carry them back** to the immediate preceding YA, where they are deducted first against any unabsorbed capital allowances and then against any trade loss of that year [e-Tax Guide: Carry-back Relief System, para 6.6; e-Tax Guide: Carry-back Relief System, para 6.8].  
- **Transfer them to a related company** under the group‑relief system [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 6.5; e-Tax Guide: Renovation or Refurbishment Works, para 7.2].

**Conditions / exceptions**

- The carry‑back relief requires the same business test (trade losses are eligible even if the business test does not apply to unabsorbed capital allowances) [e-Tax Guide: Carry-back Relief System, para 6.2].  
- For companies, the share‑holding test must also be met for carry‑forward or carry‑back [e-Tax Guide: Carry-back Relief System, para 6.6; e-Tax Guide: Carry-back Relief System, para 6.2].  
- If the first YA only generates concessionary or tax‑exempt income, the pre‑commencement expenses can be deducted against that income [e-Tax Guide: Expenses Incurred Prior to Commencement of Business, para 2.4].  

Thus, any unused pre‑opening deductible expenses can be used to reduce current, past or future taxable income, or be transferred to a group company, subject to the above tests.

*groq:openai/gpt-oss-120b; citation precision 0.17*

### q09: What facts will IRAS ask for when working out the date on which a company's business actually began?

Gold: DC:4.3, DC:2.2

IRAS (the Comptroller of Income Tax) will ask for the following facts to determine the actual date a company’s business commenced:

- A description of the taxpayer’s main business and the activities it carries out [e-Tax Guide: Date of Commencement of Business, para 2.2]  
- A description of the profit‑making structure of that business [e-Tax Guide: Date of Commencement of Business, para 2.2]  
- Confirmation whether the company has begun its day‑to‑day business operations [e-Tax Guide: Date of Commencement of Business, para 2.2]  
- A chronological list of key events that led to the profit‑making structure becoming operationally ready and the time the taxpayer started its ordinary business activities [e-Tax Guide: Date of Commencement of Business, para 2.2]

(The same four items are reiterated in the guide’s “Information to determine the date of commencement of business” section [e-Tax Guide: Date of Commencement of Business, para 4.3].)  

IRAS will also distinguish preparatory or preliminary activities (e.g., signing contracts, obtaining loans, building infrastructure) from regular day‑to‑day activities when assessing these facts [e-Tax Guide: Date of Commencement of Business, para 4.4].

*groq:openai/gpt-oss-120b; citation precision 0.67*

### q10: My client spent its first year negotiating its main supply contract, arranging bank financing and building its factory. Has it started business for tax purposes?

Gold: DC:4.4, DC:4.1

No – the client has not yet commenced business for tax purposes.  

- The activities described (negotiating a supply contract, arranging financing and building the factory) are “pre‑paratory or preliminary” work undertaken before the taxpayer is in a position to derive income [e-Tax Guide: Date of Commencement of Business, para 4.4].  
- Under the ITA the date of commencement is the day the profit‑making structure is in place **and** the first commercial activity is started [e-Tax Guide: Date of Commencement of Business, para 4.1; e-Tax Guide: Date of Commencement of Business, para 2.1]. For a manufacturer the date is when commercial production begins, not when the plant is built [e-Tax Guide: Date of Commencement of Business, para 6].  
- Until that commercial‑production (or first sale/receipt of revenue) occurs, all outgoings are “pre‑commencement expenses” and are not deductible [e-Tax Guide: Date of Commencement of Business, para 3.2; e-Tax Guide: Date of Commencement of Business, para 2.3].  

Thus, because the client is still only carrying out preparatory work and has not begun its first commercial activity, it is regarded as not having started business for tax purposes. (Deduction of such expenses would only be possible under s 14R for expenses incurred up to 12 months before the eventual deemed date of commencement, once that date is established.)

*groq:openai/gpt-oss-120b; citation precision 0.33*

### q26: What GST rate must a GST-registered company charge on its standard-rated supplies?

Gold: none (out of scope)

I can't answer this from the Income Tax Act 1947 and the IRAS e-Tax guides I have.

*groq:openai/gpt-oss-120b; citation precision n/a*

### q27: How much buyer's stamp duty does a company pay when it buys a shophouse for its own business use?

Gold: none (out of scope)

I can't answer this from the Income Tax Act 1947 and the IRAS e-Tax guides I have.

*groq:openai/gpt-oss-120b; citation precision n/a*

### q28: What property tax rate applies to the annual value of a company's commercial premises?

Gold: none (out of scope)

I can't answer this from the Income Tax Act 1947 and the IRAS e-Tax guides I have.

*groq:openai/gpt-oss-120b; citation precision n/a*

