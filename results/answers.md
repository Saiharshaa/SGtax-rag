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

## `baseline`

### q01: Two Singapore companies are each 80% owned by the same Hong Kong-incorporated parent. Can one of them set its current-year losses against the other's profits?

Gold: 37B, GR:6.1, GR:6.3

No. Group relief can only be used between Singapore‑incorporated companies that are members of the same group, and a “relevant holding company” must itself be Singapore‑incorporated. The guide states that a group must consist of a Singapore‑incorporated company and its Singapore‑incorporated group members, and that the 75 % shareholding test is applied to a Singapore‑incorporated holding company (or a third Singapore‑incorporated holding company) [e-Tax Guide: Group Relief System]. An example in the guide shows that when the ultimate parent is not Singapore‑incorporated, the companies are not treated as members of the same group for group‑relief purposes [e-Tax Guide: Group Relief System]. Since the 80 % owner is a Hong Kong‑incorporated parent, the two Singapore companies are not in the same group under the group‑relief rules, so one cannot transfer its current‑year losses to offset the other’s profits.

*groq:openai/gpt-oss-120b; citation precision 0.50*

### q02: A subsidiary closes its books on 31 March but its sister company has a 31 December year end. Can unused capital allowances be passed from one to the other?

Gold: 37B, GR:9.1

No. Under the group relief system loss items – which include unused capital allowances – can only be transferred between group companies that have the same accounting year‑end. If the companies have different year‑ends, the loss items cannot be transferred [e-Tax Guide: Group Relief System].  

The sources do not mention any exemption that would allow a transfer despite the differing year‑ends, so the capital allowances must remain with the subsidiary that incurred them.

*groq:openai/gpt-oss-120b; citation precision 0.00*

### q03: A company filed its return showing a profit, but IRAS's assessment turned the result into a loss. How long does it have to file the form needed to pass that loss to a sister company?

Gold: 37B, GR:14.2

It must file the transferor form within **2 months of the date of the IRAS notice of assessment** that shows the loss — i.e. submit Form GR A within that 2‑month period [e-Tax Guide: Group Relief System].  

- The loss can then be transferred to the sister (claimant) company, which must also file its claimant form (Form GR B) within 2 months of the same notice.  
- If either Form GR A or Form GR B is not lodged within the 2‑month window, the CIT will not allow the loss transfer.

*groq:openai/gpt-oss-120b; citation precision 1.00*

### q04: The profitable subsidiary wants to pay the loss-making subsidiary for the tax losses it absorbs. Can the payer deduct that payment, and is it taxable for the company receiving it?

Gold: GR:16.1

The payment itself is not a deductible expense – loss items are transferred under the group‑relief rules, not by a taxable payment.  
- Under the Income Tax Act, a “qualifying deduction” (loss, capital allowance or donation) is **transferred** to a claimant company, not paid out as a chargeable amount [Income Tax Act 1947] (para 6‑9).  
- The group‑relief system sets out the order in which loss items are transferred and set‑off against assessable income, but it does **not** treat a cash payment for the loss as a deductible expense [e-Tax Guide: Group Relief System] (“The loss items of a transferor are transferred out in the order as follows…”) and [e-Tax Guide: Group Relief System] (“The loss items are claimed in the same order as item 2 above”).  

Therefore:  
- The profitable subsidiary cannot deduct a cash payment made to the loss‑making subsidiary for the purpose of absorbing its losses (the Act provides for loss‑item transfer, not a deductible payment).  
- The loss‑making subsidiary does not include the amount received as taxable income; it merely transfers its loss items to the claimant under the group‑relief provisions.  

**Part not covered:** The sources do not explicitly state the tax treatment of a cash payment for loss absorption, only the mechanics of loss‑item transfer.

*groq:openai/gpt-oss-120b; citation precision 0.00*

### q05: A new company makes its first sale in March 2024 and has a 31 December year end. How far back before 1 January 2024 can its revenue expenses still be deducted?

Gold: 14R, PC:4.2

Revenue (ordinary) expenses can be deducted for the year in which the business first earns a dollar of receipt (the “deemed date of commencement”) if they were incurred **up to 12 months before that deemed date** [e-Tax Guide: Expenses Incurred Prior to Commencement of Business] 2.2‑2.3; [e-Tax Guide: Expenses Incurred Prior to Commencement of Business] 4.2.  

- First sale (first dollar of receipt) = March 2024 → deemed date of commencement = 1 January 2024 (first day of the accounting year).  
- Therefore, revenue expenses incurred **as early as 1 January 2023** (i.e., within the 12 months preceding the deemed date) are allowable deductions in the 2024 basis period.  

(Only expenses incurred on or after 25 March 2016 are covered by this rule.)

*groq:openai/gpt-oss-120b; citation precision 0.50*

### q06: In its first year a company earns both normally taxed income and income taxed at a concessionary rate. How are its set-up costs from before trading began deducted when they cannot be traced to either income stream?

Gold: 14X, PC:6.1

The un‑traced set‑up costs are allocated between the normal‑rate and concessionary‑rate income in proportion to the relative size of each income stream in the first YA.

- The expense is first split between the income streams according to the proportion each stream (normal, concessionary or exempt) bears to the total income of the trade in that basis period, as the Comptroller deems reasonable [Income Tax Act 1947].  
- The e‑Tax Guide confirms that any pre‑commencement or s14R expenses that cannot be directly attributed are “allocated to the respective income streams based on income‑apportionment” (e.g., turnover, gross profit, or a bank‑specific ratio) [e-Tax Guide: Expenses Incurred Prior to Commencement of Business].  
- If the allocated amount exceeds the income of a stream, the excess forms part of the trade loss, which may be offset against other income in the same YA, carried forward, transferred under group relief, or carried back to the preceding YA [e-Tax Guide: Expenses Incurred Prior to Commencement of Business].  

**Conditions / exceptions**  
- The rule applies to expenses incurred on or after 25 Mar 2016 [Income Tax Act 1947].  
- The expense must be a qualifying pre‑commencement or s14R expense (e.g., IP protection, R&D, R&R, design) [e-Tax Guide: Expenses Incurred Prior to Commencement of Business].  
- If the company’s income in the basis period consists solely of concessionary or solely of exempt income, the expense is deducted against that income alone [Income Tax Act 1947].

*groq:openai/gpt-oss-120b; citation precision 0.75*

### q07: Can a company whose property investment business is taxed under section 10D deduct revenue expenses it incurred before it earned any rental income?

Gold: 14R

No. A company whose property‑investment business is taxed under section 10D cannot deduct revenue expenses incurred before it earns any rental income.  

- Under section 14(1) “previous expenses” are deductible only if the expense is incurred no earlier than 12 months before the first day of the applicable basis period [Income Tax Act 1947].  
- However, subsection (4) of that provision expressly states that this rule **does not apply to the business of making investments carried out by a company or trustee of a property trust, to which section 10D applies** [Income Tax Act 1947].  

Therefore, pre‑rental‑income revenue expenses are not allowable deductions for a 10D‑taxed property investment business. (The e‑Tax guide on pre‑commencement expenses ([e-Tax Guide: Expenses Incurred Prior to Commencement of Business]) relates to other business activities and does not override the specific exclusion in [Income Tax Act 1947].)

*groq:openai/gpt-oss-120b; citation precision 0.50*

### q08: A start-up's deductible expenses from before it opened are larger than the income it earns in its first year. What can it do with the unused amount?

Gold: PC:6.5

The excess pre‑commencement or s14R expenses become a trade loss. That loss can be used in any of the following ways [e-Tax Guide: Expenses Incurred Prior to Commencement of Business]:

- **Offset against other income** of the same year of assessment (YA).  
- **Carry forward** to offset taxable income in future YAs.  
- **Transfer** to a related company under the group‑relief system.  
- **Carry back** to offset income in the immediate preceding YA.  

Thus, if the start‑up’s deductible pre‑opening expenses exceed its first‑year income, the unused amount is treated as a trade loss and may be applied against current, future, group‑related or prior‑year income as listed above.

*groq:openai/gpt-oss-120b; citation precision 1.00*

### q09: What facts will IRAS ask for when working out the date on which a company's business actually began?

Gold: DC:4.3, DC:2.2

IRAS (via the Comptroller of Income Tax) will ask for the following facts to determine the actual commencement date of a business:

- A description of the taxpayer’s main business and the activities it carries on [e-Tax Guide: Date of Commencement of Business].  
- A description of the profit‑making structure of that business [e-Tax Guide: Date of Commencement of Business].  
- Whether the company has begun its day‑to‑day business operations [e-Tax Guide: Date of Commencement of Business].  
- A chronological list of key events that led to the profit‑making structure being operationally ready and the time the taxpayer started its ordinary business activities [e-Tax Guide: Date of Commencement of Business].  

These four items are the specific facts the CIT requires when examining the date of commencement [e-Tax Guide: Date of Commencement of Business].

*groq:openai/gpt-oss-120b; citation precision 1.00*

### q10: My client spent its first year negotiating its main supply contract, arranging bank financing and building its factory. Has it started business for tax purposes?

Gold: DC:4.4, DC:4.1

No – the activities you describe are regarded as **pre‑commencement (pre‑operating) work**, so the business has not yet “commenced operation” for tax purposes.  

- The CIT looks for the establishment of a profit‑making structure and the start of the first commercial activity. Negotiating a supply contract, arranging financing and building a factory are **preparatory or preliminary activities** and do not constitute day‑to‑day operations [e-Tax Guide: Date of Commencement of Business] 4.4; for a manufacturer the date of commencement is when commercial production actually begins [e-Tax Guide: Date of Commencement of Business] (Manufacturing example).  
- Consequently, all expenses incurred in that first year are **pre‑commencement expenses** and are **not deductible** under section 14(1) [e-Tax Guide: Date of Commencement of Business] 5 and [e-Tax Guide: Date of Commencement of Business] 3.2.  
- Only if the enterprise‑development concession is claimed would the business be deemed to have commenced on the first day of the accounting year in which it earns its first dollar of receipt, allowing deduction of revenue expenses incurred in that year (and, from YA 2012, one year prior) [e-Tax Guide: Date of Commencement of Business] 3.3‑3.5.  

So, absent a concession claim, the client has **not yet started business for tax purposes**; the costs incurred are non‑deductible pre‑commencement expenses.

*groq:openai/gpt-oss-120b; citation precision 0.67*

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

