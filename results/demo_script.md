# Demo video script

Narration of `demo.mp4`, with where each line starts in the video.

**0:04** This is our retrieval-augmented assistant for Singapore corporate income tax. It answers questions from the Income Tax Act 1947 and five IRAS e-Tax guides, and cites a section or paragraph for every statement.

**0:20** The app is password protected, because its index holds the text of the IRAS guides.

**0:30** It is built for tax associates at small and medium-sized accounting firms. You can start from an example, or ask your own question.

**0:40** The question is embedded with Gemini and matched against chunks that follow the structure of the law: one chunk for each subsection of the Act, and one for each paragraph of a guide.

**0:55** Every statement in the answer carries a citation. The model cites numbered sources, and our code turns each number into a legal citation, such as section 14R, subsection 2, of the Income Tax Act. So a citation can only point at a source the model was actually shown.

**1:16** The cited sources open as short excerpts, so an associate can check each citation in seconds.

**1:23** When a question names a section, keyword search and a section boost join the semantic search, because exact section numbers are where embeddings are weakest.

**1:40** The named section, 37D subsection 3, comes first, together with the guide paragraphs that explain it.

**1:48** If the Act and the guides don't cover a question, the assistant refuses instead of guessing. Here we ask about the GST rate, which is outside our sources.

**2:06** It declines, and says why.

**2:10** Finally, we compare against a naive baseline: the same model, given plain 500-token chunks without any legal structure.

**2:29** Our structure-aware version cites both the Act, section 37D, and the exact paragraphs of the carry-back guide.

**2:40** The naive baseline can only cite the whole guide, because its chunks have no section or paragraph numbers.

**2:48** On twenty-five test questions with known answers, and given the same amount of context, structure-aware chunks found 81 percent of the right sources, against 44 percent for naive chunks. Thank you for watching.
