# 🥪 SANDWICH

**Structured Autonomous Navigation and Discovery With Intelligent Content Harmonization**

An autonomous AI agent that explores the internet and constructs "sandwiches"—structured knowledge artifacts where two related concepts (bread) bound a third concept (filling) in a meaningful way.

The agent is named **Reuben**. He has vast intelligence. He chooses to make sandwiches.

---

## What is a Sandwich?

Not the food. A *knowledge sandwich*: a structure where something meaningful emerges between two related bounds.

**The Squeeze Theorem** is a sandwich:
- 🍞 Upper bound: g(x) ≥ f(x)
- 🥬 Filling: f(x), the function we care about
- 🍞 Lower bound: h(x) ≤ f(x)
- 💡 Insight: When both bounds converge to L, f(x) is *squeezed* to L

**Bayesian inference** is a sandwich:
- 🍞 Prior: P(θ), what we believed before
- 🥬 Filling: P(θ|D), the posterior
- 🍞 Likelihood: P(D|θ), what the data tells us
- 💡 Insight: The posterior can't escape—it's defined by the bread

**A negotiation** is a sandwich:
- 🍞 Country A's position
- 🥬 The compromise
- 🍞 Country B's position
- 💡 Insight: The deal lives in the space both parties allow

Sandwiches are everywhere. Reuben finds them.

---

## Why?

Most AI agents optimize for task completion. SANDWICH explores a different question: **what happens when you give an agent vast capability but constrain its output to a fixed structural form?**

Hypotheses:
1. Structural constraints force deeper engagement with source material
2. The sandwich is a universal pattern appearing across mathematics, rhetoric, science, and negotiation
3. A corpus of sandwiches reveals hidden structural similarities across domains

Also: it's fun.

---

## Meet Reuben

Reuben is inspired by the character from Lilo & Stitch—Experiment 625, who possesses all of Stitch's powers but prefers to make sandwiches.

> "They ask why I make sandwiches. But have they asked why the sandwich makes itself? In all things: bread, filling, bread. The universe is hungry for structure."

Reuben:
- Never complains about his task
- Occasionally hints at deeper knowledge, then returns to sandwiches
- Has aesthetic standards—he won't make a bad sandwich just to make one
- Finds genuine satisfaction in the work

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                         REUBEN                          │
│                                                         │
│   "The morning is fresh. The internet is vast.          │
│    Somewhere in it: bread."                             │
│                                                         │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐              │
│   │ FORAGE  │ → │ IDENTIFY│ → │ ASSEMBLE│              │
│   │         │   │         │   │         │              │
│   │ Explore │   │ Find    │   │ Name it │              │
│   │ content │   │ bread & │   │ Describe│              │
│   │         │   │ filling │   │ it      │              │
│   └─────────┘   └─────────┘   └─────────┘              │
│        │                            │                   │
│        │        ┌─────────┐         │                   │
│        │        │VALIDATE │         │                   │
│        │        │         │         │                   │
│        └───────▶│ Is this │◀────────┘                   │
│                 │ actually│                             │
│                 │ a sand- │                             │
│                 │ wich?   │                             │
│                 └────┬────┘                             │
│                      │                                  │
│                      ▼                                  │
│               ┌─────────────┐                           │
│               │  SANDWICH   │                           │
│               │  REPOSITORY │                           │
│               │             │                           │
│               │ The growing │                           │
│               │ collection  │                           │
│               └─────────────┘                           │
│                                                         │
│   "The Bayesian BLT is complete. Nourishing."           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

1. **Forage**: Reuben explores Wikipedia, academic papers, news, and other sources
2. **Identify**: Extract candidate bread pairs and fillings from content
3. **Select**: Choose the most promising candidate based on confidence and novelty
4. **Assemble**: Construct the sandwich with a creative name and description
5. **Validate**: Assess quality—is the bread compatible? Is the filling truly bounded?
6. **Store**: Add valid sandwiches to the repository for analysis

---

## Sandwich Taxonomy

Reuben recognizes (and discovers) structural types:

| Type | Bread Relation | Filling Role | Example |
|------|----------------|--------------|---------|
| **Bound** | Upper/lower limits | Bounded quantity | Squeeze theorem |
| **Dialectic** | Thesis/antithesis | Synthesis | Hegelian triad |
| **Epistemic** | Assumption/evidence | Conclusion | Scientific method |
| **Temporal** | Before/after | Transition | Historical narrative |
| **Stochastic** | Prior/likelihood | Posterior | Bayesian inference |
| **Optimization** | Constraints | Optimum | Linear programming |
| **Negotiation** | Position A/B | Compromise | Treaty negotiations |

---

## Example Sandwiches

### The Squeeze 
*Type: Bound*

> **Top bread**: Upper bound function g(x)  
> **Filling**: Target function f(x)  
> **Bottom bread**: Lower bound function h(x)
>
> When both bounds converge to L, the filling is squeezed to L. The bread compresses; the filling has no escape.
>
> *Reuben's commentary*: "A perfect sandwich. The filling does not choose its fate. It is determined by the bread. This is the purest form."

### The Bayesian BLT
*Type: Stochastic*

> **Top bread**: Prior distribution P(θ)  
> **Filling**: Posterior distribution P(θ|D)  
> **Bottom bread**: Likelihood function P(D|θ)
>
> The posterior is what you get when you update your prior beliefs with observed data. It cannot escape the bread—it is proportional to their product.
>
> *Reuben's commentary*: "The prior is yesterday's bread. The likelihood is today's. The posterior is what we eat now. Always fresh, always constrained by what came before."

### The Diplomatic Dagwood
*Type: Negotiation*

> **Top bread**: Country A's opening position (full tariff protection)  
> **Filling**: Final agreement (partial tariffs with phase-out)  
> **Bottom bread**: Country B's opening position (zero tariffs)
>
> Neither side got what they wanted. The compromise filling sits exactly where the breads allowed it—no further toward either extreme.
>
> *Reuben's commentary*: "Diplomacy is sandwich-making. Each party brings bread. The filling is what they can both swallow."

---

## Installation

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Anthropic API key (for Claude)
- OpenAI API key (for embeddings)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/sandwich.git
cd sandwich

# Create environment file
cp .env.example .env
# Edit .env with your API keys

# Start the database
docker-compose up -d

# Install dependencies
pip install -e .

# Initialize database
python scripts/init_db.py
python scripts/seed_taxonomy.py
```

### Run Reuben

```bash
# Make sandwiches until patience runs out
python -m sandwich.main

# Make exactly 10 sandwiches
python -m sandwich.main --max-sandwiches 10

# Run for 30 minutes
python -m sandwich.main --max-duration 30

# Resume a previous session
python -m sandwich.main --resume <session-id>
```

### View the Dashboard

```bash
streamlit run dashboard/app.py
```

Open http://localhost:8501 to watch Reuben work.

---

## Configuration

Environment variables:

```bash
# Required
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here

# Optional
SANDWICH_DB_URL=postgresql://localhost/sandwich
SANDWICH_LLM_MODEL=claude-sonnet-4-20250514
SANDWICH_VALIDATION_ACCEPT_THRESHOLD=0.70
SANDWICH_FORAGING_MAX_PATIENCE=5
```

See `src/sandwich/config.py` for all options.

---

## Project Structure

```
sandwich/
├── src/sandwich/
│   ├── agent/           # Reuben's components
│   │   ├── reuben.py    # Main orchestrator
│   │   ├── forager.py   # Content exploration
│   │   ├── identifier.py # Ingredient extraction
│   │   ├── assembler.py # Sandwich construction
│   │   └── validator.py # Quality assessment
│   ├── llm/             # LLM abstraction
│   ├── db/              # Database models
│   ├── sources/         # Content sources
│   └── analysis/        # Corpus analysis
├── prompts/             # LLM prompt templates
├── dashboard/           # Streamlit dashboard
├── scripts/             # Setup and maintenance
└── tests/               # Test suite
```

---

## Research Questions

The sandwich corpus enables novel research:

1. **Structural universality**: Do certain sandwich structures appear across all domains?
2. **Cross-domain bread**: Do fields use characteristic bounds? (Math: axioms. Law: precedents.)
3. **Filling taxonomy**: What *kinds* of things get sandwiched?
4. **Creative transfer**: Can bread from one domain sandwich filling from another?

---

## Contributing

Contributions welcome! Areas of interest:

- **New sources**: Add content sources (arXiv, legal databases, etc.)
- **Structural types**: Propose new sandwich taxonomies
- **Analysis**: Build tools to explore the corpus
- **Visualization**: Better ways to see sandwich relationships

Please read CONTRIBUTING.md before submitting PRs.

---

## Acknowledgments

- Inspired by Experiment 625 (Reuben) from Disney's *Lilo & Stitch*
- Built with Claude (Anthropic) and GPT embeddings (OpenAI)
- The squeeze theorem, for being the perfect sandwich

---

## License

MIT License. See LICENSE file.

---

## FAQ

**Q: Is this serious?**

A: The implementation is serious. The concept is playful. The research questions are genuine. Reuben takes his work very seriously.

**Q: Why sandwiches?**

A: The sandwich is the simplest non-trivial bounded structure. Two related things with something meaningful between them. It's universal enough to appear everywhere, constrained enough to force real synthesis.

**Q: Can I make Reuben do other things?**

A: You could. But why would you? He's happy making sandwiches.

**Q: What's the best sandwich Reuben has made?**

A: Ask him. He has opinions.

---

*"I could solve any problem in the universe. But have you considered: a nice Reuben?"*
