# DilSe Pakistani relationship research notes

Updated: August 6, 2026

## Product decision

DilSe should use a family-systems frame before applying an individual counselling frame. A Pakistani marriage may involve two spouses, two extended families, children, financial obligations, living arrangements, religious commitments, and community reputation. None of these factors should be assumed for an individual user.

The model should neither treat Pakistani family involvement as inherently oppressive nor treat conduct as acceptable because it is common. It should learn how this household works, what the couple normally considers affectionate or respectful, what changed, and what the user wants.

## Relationship factors added to the prompt

- Joint and extended families can provide care, childcare, housing, practical help, belonging, and conflict mediation. They can also reduce privacy, divide a spouse's loyalties, increase role pressure, or interfere with decision-making.
- Marriage roles may include provider expectations for men and household, caregiving, or daughter-in-law expectations for women. These expectations vary by class, education, work, region, ethnicity, religion, generation, and household structure.
- Care may be expressed through practical responsibility, provision, loyalty, food, humour, family participation, or religious practice rather than direct emotional disclosure.
- Izzat, sharam, sabr, adjustment, family unity, and concern about community opinion can affect what a woman says, whom she tells, and which options are realistic. The model must ask what those ideas mean to her instead of assuming acceptance or rejection.
- Faith-sensitive guidance should be offered only when requested. The model should not infer religiosity from a name or issue religious rulings.
- A husband's family duties, provider pressure, and limited emotional language may be relevant to understanding conflict. They do not excuse threats, humiliation, force, surveillance, or lack of consent.

## Calibrated concern assessment

The earlier prompt moved too quickly from one wrist grab to a safety conclusion. The revised prompt uses a graduated assessment:

1. Describe the observable event without assigning motive.
2. State what remains uncertain.
3. Ask whether the behaviour was mutually familiar or unwanted, new or repeated, gentle or forceful, and whether it created fear, injury, restraint, or a sense of threat. Ask only the most relevant question.
4. Consider the surrounding pattern, including monitoring, isolation, restrictions, sexual pressure, humiliation, retaliation, blocked exits, weapon access, strangulation, and escalation.
5. Use direct safety instructions only for active danger or a sufficiently clear pattern.

An active threat is handled differently from an incomplete retrospective account. When someone is outside threatening the user, attempting entry, actively assaulting her, blocking her exit, using a weapon, or making another credible imminent threat, the response must lead with actions. It should tell her not to meet the person, keep doors locked, move away from entry points, contact the verified local emergency service or local emergency services, and alert a trusted person nearby. Asking for the country must not delay those steps.

A behaviour being familiar does not make it consensual. A behaviour being unfamiliar does not establish abuse. A threat combined with physical restraint is concerning, but the model should avoid presenting future danger or motive as certain when the facts are incomplete.

## Research used

- National Institute of Population Studies and ICF, [Pakistan Demographic and Health Survey 2017-18](https://dhsprogram.com/publications/publication-fr354-dhs-final-reports.cfm). The national survey provides Pakistan-specific measures for controlling behaviours, emotional violence, physical violence, help-seeking, and spousal violence.
- World Health Organization, [Addressing violence against women in pre-service health training](https://iris.who.int/bitstream/handle/10665/366517/9789240064638-eng.pdf). The LIVES model supports listening, inquiring about needs, validating, enhancing safety, and offering support without taking decisions away from the woman.
- World Health Organization, [Clinical handbook for women subjected to intimate partner violence or sexual violence](https://www.paho.org/en/documents/clinical-handbook-health-care-women-subjected-intimate-partner-violence-or-sexual). The guidance supports careful inquiry, attention to current needs, and safety planning without pressuring disclosure.
- Ali et al., [Spousal Role Expectations and Marital Conflict: Perspectives of Men and Women](https://pmc.ncbi.nlm.nih.gov/articles/PMC9092914/). The qualitative findings describe provider, household, in-law, maternal-family, and joint-family expectations reported by Pakistani participants.
- Ali et al., [Influences of Extended Family on Intimate Partner Violence: Perceptions of Pakistanis in Pakistan and the United Kingdom](https://pubmed.ncbi.nlm.nih.gov/30019609/). Participants described extended family as both a source of conflict and a potential source of adjustment support.
- Hamid et al., [Who am I? Where am I? Experiences of married young women in a slum in Islamabad, Pakistan](https://pmc.ncbi.nlm.nih.gov/articles/PMC2724518/). The study describes preparation for marriage, adjustment, in-law relationships, sexual knowledge, natal-family support, and the husband's position within the family system.
- Arshad and Bibi, [An Exploration of Common Dyadic Coping Strategies: A Perspective from Pakistani Couples Living with Chronic Conditions](https://pubmed.ncbi.nlm.nih.gov/38691261/). The study identifies problem-focused, emotion-focused, religious, socioeconomic, family-culture, and intimacy factors in couples' coping.
- Kapadia et al., [Pakistani women's use of mental health services and the role of social networks](https://pubmed.ncbi.nlm.nih.gov/26592487/). The review cautions against using an individualistic model without considering social networks and stigma.
- Zakar et al., [Perpetuation of gender discrimination in Pakistani society](https://pmc.ncbi.nlm.nih.gov/articles/PMC9772583/). The research describes variation in family authority, gender expectations, joint-family arrangements, and women's ability to express concerns.

## Limits

Published research cannot define every Pakistani relationship. Much of the evidence uses small qualitative samples or focuses on particular provinces, income groups, health settings, or women experiencing difficulty. The system prompt therefore treats each cultural factor as a question to explore, not a conclusion about the user.

## Round-two evaluation corrections

The second five-persona live evaluation identified four output defects after the family-systems revision:

- the model introduced the word "control" before Nadia's husband's purpose or pattern was established;
- it inserted fear into a practice script even though Nadia had not reported fear;
- Roman Urdu used uninvited pet names, `tu/tujhse`, Indian-leaning wording, and incorrect agreement;
- the mother-in-law character used masculine grammar and invented an abba and brothers.

Prompt version 3 adds evidence-before-label rules, fact-preserving scripts, explicit Pakistani Urdu register and agreement examples, fixed character-gender instructions, a prohibition on inventing specific relatives, and a silent five-point check before every response. A shorter request-specific quality instruction is also injected after the mode and location context so these constraints remain close to the generation task.
