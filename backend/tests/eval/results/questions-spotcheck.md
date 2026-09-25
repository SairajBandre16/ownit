# Question spot-check (P6 acceptance)

30 questions generated from `tests/eval/paragraphs_*.txt` paragraphs 17-24 of each file (not used while tuning), reviewed by hand.

First pass: 27/30 grammatical. The three failures ("How does cloud computing affect the way?", "Why is your lower value likely?", "Why is the difference probably?") were fixed (empty-noun objects and hedge-only predicates are now skipped) and added as must-not-fire unit tests. Second pass below: 30/30 grammatical.

| # | set | type | question | key / level | verdict |
|---|---|---|---|---|---|
| 1 | engineering | cloze | The magnitude of this voltage is dependent on the _____ between the hot and cold junctions. | temperature difference | ok |
| 2 | engineering | mcq | Two out of eight _____ showed surface cracks near the heat-affected zone. | specimens | ok |
| 3 | engineering | tf | Inverse kinematics was not utilized in order to calculate the joint angles for a given end-effector position. | false | ok |
| 4 | engineering | cloze | When the junction is heated, a _____ is generated due to the Seebeck effect. | voltage | ok |
| 5 | engineering | mcq | The design traffic was estimated to be 20 _____ (msa). | million standard axles | ok (the '(msa)' after the blank is a small hint) |
| 6 | engineering | tf | The measured bandwidth was 120 MHz, which is slightly narrower than the simulated value. | true | ok |
| 7 | engineering | cloze | The _____ was −28 dB at the resonant frequency, as shown in Fig. 4. | simulated return loss | ok |
| 8 | engineering | viva | What does IRC stand for, and what does it do in your project? | L1 abbreviation | ok |
| 9 | engineering | viva | What does BER stand for, and what does it do in your project? | L1 abbreviation | ok |
| 10 | engineering | viva | Compare the measured bandwidth and the simulated value. Which suits this project better, and why? | L4 comparison | ok |
| 11 | ai | cloze | _____ is an essential aspect of the manufacturing process. | Quality control | ok |
| 12 | ai | mcq | An _____ is a combination of hardware and software designed to perform a specific function. | embedded system | ok |
| 13 | ai | tf | Embedded systems are not an integral part of modern electronic devices. | false | ok |
| 14 | ai | cloze | _____ is a fundamental technology in modern communication systems. | Digital signal processing | ok |
| 15 | ai | mcq | _____ have the ability to generate large forces with relatively compact components, which is a testament to their efficiency. | hydraulic systems | ok |
| 16 | ai | tf | In today's world, DSP is utilized in a myriad of applications, from audio processing to radar. | true | ok |
| 17 | ai | cloze | Pascal's law forms the basis of _____. | hydraulic system design | ok |
| 18 | ai | viva | What does DSP stand for, and what does it do in your project? | L1 abbreviation | ok |
| 19 | ai | viva | How do devices such as pacemakers and prosthetic limbs affect the quality of life? | L2 effect | ok |
| 20 | ai | viva | Explain how fouling changes performance. | L2 effect | ok |
| 21 | student | cloze | Our lower value is likely due to heat gain through the _____ and the fact that the compressor was quite old. | pipes | ok |
| 22 | student | mcq | The _____ kept disconnecting when the robot was more than about 8 m away. | Bluetooth module | ok |
| 23 | student | tf | The pump in our test rig was not supposed to deliver 20 litres per minute but we only got about 14. | false | ok (grammatical; negating 'supposed to' makes an odd false statement) |
| 24 | student | cloze | The theoretical _____ for the same temperatures is about 4.1. | COP | ok |
| 25 | student | mcq | This will matter later when we compare the _____ results. | shear strength | ok |
| 26 | student | tf | In the refrigeration lab, the COP we calculated from our readings was 2.4. | true | ok |
| 27 | student | cloze | What helped was working out the _____ contribution of each pole and zero separately and then adding them. | phase | ok |
| 28 | student | viva | What does COP stand for, and what does it do in your project? | L1 abbreviation | ok |
| 29 | student | viva | Why was a grid of 10 m squares used here and not an alternative? | L3 choice | ok |
| 30 | student | viva | What are the limitations of solids assignment in this project? | L4 evaluate | ok (awkward: the keyphrase is a fragment of "the mechanics of solids assignment") |
