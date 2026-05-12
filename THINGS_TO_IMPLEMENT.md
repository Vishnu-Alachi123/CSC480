# Things to Implement

---

- [ ] **Evaluate based on player betting**

  Track how opponents have been betting throughout the hand and across rounds. A player who raises pre-flop and continues betting on the flop is likely strong. Use this signal to adjust your own decisions — if someone is betting aggressively, a marginal hand becomes a fold.

---

- [ ] **Betting size based on rank of hand**

  Right now `SimpleAgent` always raises the minimum. The raise amount should scale with hand strength — a royal flush should bet much more than a straight. Define a mapping from `HandRank` to a bet sizing (e.g. a fraction of the pot) so the agent extracts maximum value from strong hands.

---

- [ ] **Evaluate probability of opponents' hands**

  Given the community cards and the betting behaviour you've observed, estimate what range of hands each opponent is likely holding. For example, if the board shows three hearts and an opponent keeps raising, they probably have a flush. This narrows down what cards are left in the deck and helps you decide whether your hand is actually winning.

---

- [ ] **Probability of our best hand**

  Run a Monte Carlo simulation — deal out the remaining community cards randomly many times and count how often your hole cards produce the best hand at the table. This gives a win probability (equity) that is much more useful than just the current hand rank, especially pre-flop and on the flop when the board is still incomplete.
