# Demo video script

Narration of `demo_grab.mp4`, with where each line starts in the video.

**0:10** Imagine the in-house tax team at Grab in Singapore. Grab runs several Singapore companies, for ride-hailing, food delivery and payments, and many business decisions have a tax angle. Our assistant answers those questions from the Income Tax Act and the IRAS e-Tax guides, and cites every point. This is an illustrative scenario, not advice to or from Grab.

**0:35** The app is password protected, because its index holds the text of the IRAS guides.

**0:47** First question. Grab's food-delivery company makes a loss this year, while ride-hailing is profitable. Can the group use that loss now?

**1:11** Yes, through group relief, if both are Singapore companies in the same group with the same year-end. Each condition is cited to the IRAS guide, so the tax team can check it in seconds. For a group like Grab, that turns a start-up loss into a tax saving this year instead of later.

**1:32** Second question. Grab is refurbishing its Singapore offices. How much can it claim, and when?

**1:49** Up to three hundred thousand dollars for each fixed three-year block, deducted over three years, or in a single year by election. That is a cash-flow decision the finance team can make with the rule in front of them.

**2:03** Third, a new subsidiary makes a loss. Can it carry it back, and by when must it decide? We compare our assistant with a naive baseline: the same model and the same search, but plain 500-token chunks.

**2:30** Our assistant cites the Act, section 37D, and the exact paragraphs of the carry-back guide: the deadline is the tax return, and the election can't be withdrawn.

**2:44** The baseline reaches a similar answer, but can only cite the whole guide. A reviewer can't check that.

**2:52** Finally, a GST question. GST is outside our sources, so the assistant refuses instead of guessing.

**3:07** It declines, and says why.

**3:11** For a business like Grab, that means faster answers on reliefs such as group relief, refurbishment deductions and loss carry-back, each traceable to the law. On twenty-five test questions, with the same search and the same amount of context, our structure-aware chunks found 81 percent of the right sources against 67 percent for naive chunks. Thank you for watching.
