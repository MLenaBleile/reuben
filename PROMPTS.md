# SANDWICH Implementation Prompts

## How to Use This Document

Feed each prompt to Claude Code **one at a time**. Do not proceed to the next prompt until:

1. The code is implemented
2. The tests pass
3. You've manually reviewed the output

The prompts are ordered by dependency. Prompt 3 (Validator) is the critical gate—do not proceed past it until the validator reliably separates good sandwiches from bad.

Estimated total time: 4-8 hours of Claude Code execution + your review cycles.

---

## Prompt 1: Project Setup & Database

```
Read SPEC.md thoroughly before starting. This is your source of truth.

Set up the project structure and database schema.

Tasks:
1. Create the directory structure from SPEC.md Section 13.3
2. Set up pyproject.toml with dependencies from Section 13.1  
3. Create the configuration classes from Section 13.2 in src/sandwich/config.py
4. Implement the full database schema from Section 9.2 in src/sandwich/db/
5. Create a docker-compose.yml with:
   - Postgres 15 with pgvector extension
   - Exposed on port 5432
   - Volume for data persistence
6. Write scripts/init_db.py that:
   - Connects to the database
   - Creates all tables from the schema
   - Creates indexes
7. Write scripts/seed_taxonomy.py that:
   - Populates the 10 initial structural types from Section 4.2
   - Sets is_proposed=FALSE for all initial types

Do NOT implement any agent logic yet. Infrastructure only.

Acceptance test:
```bash
docker-compose up -d
python scripts/init_db.py
python scripts/seed_taxonomy.py
# Then verify in psql:
# SELECT * FROM structural_types;  -- should show 10 rows
```
```

---

## Prompt 2: Error Taxonomy & LLM Abstraction

```
Implement the error handling and LLM abstraction layers.

Reference: SPEC.md Sections 6.1, 6.2, 7.1, 7.2

Tasks:
1. Implement the error taxonomy in src/sandwich/errors/exceptions.py:
   - SandwichError (base)
   - RetryableError (rate limits, network, timeout)
   - ContentError (too short, non-english, low quality, duplicate)
   - ParseError (malformed JSON, missing fields)
   - FatalError (database down, config error, auth error)
   
2. Implement retry logic in src/sandwich/llm/retry.py:
   - RetryConfig dataclass (max_retries, base_delay, max_delay, exponential_base)
   - with_retry async function with exponential backoff and jitter
   
3. Implement LLM interface in src/sandwich/llm/interface.py:
   - SandwichLLM abstract base class with methods:
     - generate_curiosity()
     - identify_ingredients()
     - assemble_sandwich()
     - assess_quality()
     - generate_commentary()
   - EmbeddingService abstract base class with methods:
     - embed_single()
     - embed_batch()

4. Implement Anthropic LLM in src/sandwich/llm/anthropic.py:
   - AnthropicSandwichLLM class implementing SandwichLLM
   - Should accept an observer for logging
   - Should use retry logic for all API calls

5. Implement embedding service in src/sandwich/llm/embeddings.py:
   - OpenAIEmbeddingService implementing EmbeddingService
   - Include in-memory cache
   - Batch API calls efficiently

6. Implement LLM observer in src/sandwich/observability/logging.py:
   - Log all LLM calls to llm_call_log table
   - Track: prompt_hash, latency, tokens, cost, errors

Write tests in tests/test_llm.py:
- test_retry_exponential_backoff: verify delays increase exponentially
- test_retry_max_attempts: verify gives up after max retries
- test_error_classification: verify each error type routes correctly
- test_embedding_caching: verify cache hits don't call API

Do NOT implement actual prompts yet—just the infrastructure.
```

---

## Prompt 3: The Validator (CRITICAL GATE)

```
⚠️ THIS IS THE MOST IMPORTANT COMPONENT. DO NOT PROCEED UNTIL IT WORKS.

Implement the validator from SPEC.md Section 3.2.6.

Reference: Sections 3.2.6, 14.5, 15

Tasks:
1. Create prompts/validator.txt with the template from Section 14.5

2. Create src/sandwich/agent/validator.py with:
   - ValidationConfig dataclass (weights, thresholds)
   - ValidationResult dataclass (all scores, recommendation, rationale)
   - validate_sandwich() async function implementing hybrid validation:
     
     a) LLM-judged components:
        - Call LLM with validator prompt
        - Parse bread_compatibility and containment scores
        - Use parse_with_recovery for robustness
     
     b) Embedding-based components:
        - nontrivial_score = 1 - max(sim(filling, bread_top), sim(filling, bread_bottom))
        - novelty_score = 1 - max_similarity_to_corpus (or 1.0 if corpus empty)
     
     c) Combine:
        - overall = weighted sum of all 4 scores
        - recommendation based on thresholds

3. Implement parse_with_recovery in src/sandwich/llm/retry.py:
   - Try to parse JSON from response
   - On failure, retry with stricter prompt
   - Max 2 attempts before raising ParseError

4. Create tests/test_validator.py with these test cases:

GOOD SANDWICHES (expected validity > 0.7):

test_squeeze_theorem:
  bread_top: "Upper bound function g(x) where g(x) ≥ f(x)"
  filling: "Target function f(x) whose limit we seek"
  bread_bottom: "Lower bound function h(x) where h(x) ≤ f(x)"
  structure_type: "bound"
  description: "When both bounds converge to L, the filling is squeezed to L"
  containment_argument: "f(x) cannot escape the bounds; its limit is determined by theirs"

test_bayesian_blt:
  bread_top: "Prior distribution P(θ) encoding beliefs before data"
  filling: "Posterior distribution P(θ|D) updated beliefs"
  bread_bottom: "Likelihood function P(D|θ) probability of data given parameter"
  structure_type: "stochastic"
  description: "The posterior is proportional to prior times likelihood"
  containment_argument: "The posterior has no independent existence without both prior and likelihood"

test_regulatory_reuben:
  bread_top: "Minimum safety standards required by law"
  filling: "Actual company safety practices"
  bread_bottom: "Maximum cost constraints from budget"
  structure_type: "optimization"
  description: "Company practices must satisfy regulations while staying under budget"
  containment_argument: "Practices below minimum are illegal; above maximum are unaffordable"

BAD SANDWICHES (expected validity < 0.5):

test_trivial_sandwich:
  bread_top: "Dogs"
  filling: "Dogs"
  bread_bottom: "Canines"
  # Should fail nontrivial check - filling is same as bread

test_unrelated_bread:
  bread_top: "The color blue"
  filling: "Monetary policy decisions"
  bread_bottom: "Guitar string tension"
  # Should fail bread_compat check - no relationship between breads

test_no_containment:
  bread_top: "Breakfast time"
  filling: "The concept of justice"
  bread_bottom: "Dinner time"
  # Should fail containment check - justice is not bounded by meal times

Run all 6 tests. Tune the validator prompt and thresholds until:
- All 3 good sandwiches score > 0.7
- All 3 bad sandwiches score < 0.5
- Separation is clean (no scores between 0.5 and 0.7)

Print detailed scores for each sandwich during testing.

⚠️ DO NOT PROCEED TO PROMPT 4 UNTIL ALL TESTS PASS.
```

---

## Prompt 4: Preprocessor

```
Implement the preprocessor from SPEC.md Section 3.2.2.

Reference: Section 3.2.2

Tasks:
1. Create src/sandwich/agent/preprocessor.py with:

   - PreprocessResult dataclass:
     - text: Optional[str]
     - skip: bool
     - skip_reason: Optional[str]  # 'too_short', 'non_english', 'low_quality', 'boilerplate'
     - quality_score: float
     - original_length: int
     - processed_length: int
     - language: str
   
   - preprocess() function implementing the pipeline:
     
     Stage 1: HTML extraction
     - If content_type is HTML, use readability-lxml to extract article
     - Otherwise pass through
     
     Stage 2: Boilerplate removal
     - Remove common patterns: cookie notices, subscribe prompts, nav menus
     - Use configurable regex patterns
     
     Stage 3: Language detection
     - Use langdetect library
     - Skip if not English (configurable)
     
     Stage 4: Length normalization
     - Skip if < min_length (default 200 chars)
     - Truncate if > max_length (default 10000 chars)
     - Smart truncation: don't cut mid-sentence
     
     Stage 5: Quality assessment
     - Compute quality_score based on:
       - Sentence length variance (high = good)
       - Unique word ratio (> 0.3 = good)
       - Punctuation density (0.02-0.08 = good)
       - Has multiple paragraphs (good)
     - Skip if quality_score < threshold (default 0.4)

2. Write tests in tests/test_preprocessor.py:

test_html_extraction:
  - Fetch a real Wikipedia article HTML
  - Verify article text is extracted
  - Verify navigation, footers removed

test_boilerplate_removal:
  - Input text with "Subscribe to our newsletter" and "Cookie policy"
  - Verify these are removed

test_language_detection:
  - English text → detected as 'en', not skipped
  - French text → detected as 'fr', skipped with reason 'non_english'

test_length_normalization:
  - 100 char text → skipped with reason 'too_short'
  - 50000 char text → truncated to ~10000, ends at sentence boundary

test_quality_scoring:
  - Well-written article → quality_score > 0.6
  - Repetitive spam text → quality_score < 0.3

test_full_pipeline:
  - Fetch Wikipedia article on "Squeeze theorem"
  - Run through preprocessor
  - Verify clean text output suitable for identifier
```

---

## Prompt 5: Identifier and Selector

```
Implement the identifier and selector from SPEC.md Sections 3.2.3 and 3.2.4.

Reference: Sections 3.2.3, 3.2.4, 14.3

Tasks:
1. Create prompts/identifier.txt with template from Section 14.3

2. Create prompts/personality_preamble.txt with template from Section 14.1

3. Create src/sandwich/agent/identifier.py with:
   
   - CandidateStructure dataclass:
     - bread_top: str
     - bread_bottom: str
     - filling: str
     - structure_type: str
     - confidence: float
     - rationale: str
   
   - IdentificationResult dataclass:
     - candidates: list[CandidateStructure]
     - no_sandwich_reason: Optional[str]
   
   - identify_ingredients() async function:
     - Load and format prompt with content
     - Call LLM
     - Parse response with recovery
     - Return IdentificationResult

4. Create src/sandwich/agent/selector.py with:
   
   - SelectionConfig dataclass (min_confidence, novelty_weight, diversity_weight)
   
   - SelectedCandidate dataclass:
     - candidate: CandidateStructure
     - final_score: float
     - novelty_bonus: float
     - diversity_bonus: float
     - rationale: str
   
   - select_candidate() function implementing logic from Section 3.2.4:
     - Filter by min_confidence
     - Compute novelty bonus from corpus similarity
     - Compute diversity bonus from type frequency
     - Return highest scoring candidate (or None)

5. Write tests in tests/test_identifier.py:

test_squeeze_theorem_identification:
  - Preprocess Wikipedia "Squeeze theorem" content
  - Run identifier
  - Verify at least one candidate with structure_type="bound"
  - Verify confidence > 0.7

test_recipe_identification:
  - Use a cooking recipe text
  - Run identifier
  - Verify finds some structure (temporal: raw→cooked, or bound: min/max cooking time)

test_gibberish_no_candidates:
  - Use random word salad
  - Run identifier
  - Verify candidates is empty
  - Verify no_sandwich_reason is populated

test_selector_ranking:
  - Create 3 mock candidates with different confidences
  - Run selector with empty corpus
  - Verify highest confidence wins

test_selector_novelty_bonus:
  - Create 2 candidates: one similar to corpus, one novel
  - Run selector with populated corpus embeddings
  - Verify novel candidate gets bonus and may win despite lower confidence

test_selector_threshold:
  - Create candidates all below min_confidence
  - Run selector
  - Verify returns None
```

---

## Prompt 6: Assembler

```
Implement the assembler from SPEC.md Section 3.2.5.

Reference: Sections 3.2.5, 14.4

Tasks:
1. Create prompts/assembler.txt with template from Section 14.4

2. Create src/sandwich/agent/assembler.py with:
   
   - AssembledSandwich dataclass:
     - name: str
     - description: str
     - containment_argument: str
     - reuben_commentary: str
     - bread_top: str
     - bread_bottom: str
     - filling: str
     - structure_type: str
     - source_content_snippet: str  # First 500 chars of source
   
   - assemble_sandwich() async function:
     - Load personality preamble
     - Load and format assembler prompt
     - Call LLM
     - Parse response with recovery
     - Return AssembledSandwich

3. Write tests in tests/test_assembler.py:

test_assembler_returns_valid_json:
  - Create a candidate (squeeze theorem structure)
  - Run assembler
  - Verify all fields populated
  - Verify no parse errors

test_name_is_creative:
  - Run assembler on 3 different candidates
  - Verify names are different
  - Verify names are not generic ("Sandwich 1", "Untitled")
  - Verify names have some connection to content

test_reuben_voice:
  - Run assembler
  - Verify commentary contains no complaints
  - Verify commentary has contemplative/content tone
  - Check for phrases like "nourishing", "satisfying", "the bread..."
  - Verify no phrases like "I wish", "unfortunately", "I can't"

test_containment_argument_present:
  - Run assembler
  - Verify containment_argument is substantive (> 50 chars)
  - Verify it references the bread elements

test_full_assembly:
  - Use squeeze theorem candidate
  - Run assembler
  - Print full output for manual review
  - Verify it reads well and makes sense
```

---

## Prompt 7: Integration - Full Pipeline

```
Wire up the full sandwich-making pipeline.

Reference: SPEC.md Sections 7.3, 9.2

Tasks:
1. Create src/sandwich/agent/pipeline.py with:

   async def make_sandwich(
       content: str,
       source_metadata: SourceMetadata,
       corpus: SandwichCorpus,
       llm: SandwichLLM,
       embeddings: EmbeddingService,
       config: PipelineConfig
   ) -> Optional[StoredSandwich]:
       """
       Full pipeline: preprocess → identify → select → assemble → validate → store
       
       Returns StoredSandwich if successful, None if rejected at any stage.
       Each stage logs its outcome.
       """
       
       # 1. Preprocess
       prep_result = preprocess(content, source_metadata)
       if prep_result.skip:
           log_pipeline_outcome("preprocessing", "skipped", prep_result.skip_reason)
           return None
       
       # 2. Identify
       id_result = await identify_ingredients(prep_result.text, llm)
       if not id_result.candidates:
           log_pipeline_outcome("identification", "no_candidates", id_result.no_sandwich_reason)
           return None
       
       # 3. Select
       selected = select_candidate(id_result.candidates, corpus, config.selection)
       if not selected:
           log_pipeline_outcome("selection", "none_viable", "all below threshold")
           return None
       
       # 4. Assemble
       assembled = await assemble_sandwich(selected.candidate, prep_result.text, llm)
       
       # 5. Validate
       validation = await validate_sandwich(assembled, prep_result.text, corpus, embeddings, config.validation)
       if validation.recommendation == "reject":
           log_pipeline_outcome("validation", "rejected", validation.rationale)
           return None
       
       # 6. Generate embeddings (batch call)
       sandwich_embeddings = await generate_sandwich_embeddings(assembled, embeddings)
       
       # 7. Store
       stored = await store_sandwich(assembled, validation, sandwich_embeddings, source_metadata)
       log_pipeline_outcome("storage", "success", stored.sandwich_id)
       
       return stored

2. Implement generate_sandwich_embeddings() per Section 7.3:
   - Batch all 4 texts in single API call
   - Return SandwichEmbeddings with bread_top, bread_bottom, filling, full

3. Implement store_sandwich() that:
   - Inserts into sandwiches table
   - Creates/updates ingredients via find_or_create_ingredient (Section 10.3)
   - Links sandwich to ingredients
   - Detects and stores relations to similar sandwiches

4. Create src/sandwich/db/corpus.py with SandwichCorpus class:
   - get_all_embeddings() → np.ndarray
   - max_similarity(embedding) → float
   - get_type_frequencies() → dict[str, float]
   - is_empty() → bool

5. Write tests in tests/test_pipeline.py:

test_full_pipeline_success:
  - Fetch Wikipedia "Squeeze theorem" article
  - Create source metadata
  - Run make_sandwich()
  - Verify returns StoredSandwich
  - Verify sandwich in database
  - Verify embeddings populated
  - Verify ingredients created

test_pipeline_preprocessor_rejection:
  - Use very short content (< 200 chars)
  - Run make_sandwich()
  - Verify returns None
  - Verify logged as preprocessing skip

test_pipeline_no_candidates:
  - Use random gibberish
  - Run make_sandwich()
  - Verify returns None
  - Verify logged as no_candidates

test_pipeline_validation_rejection:
  - Construct content that will produce a trivial sandwich
  - Run make_sandwich()
  - Verify returns None
  - Verify logged as validation rejected

test_ingredient_reuse:
  - Make two sandwiches with similar bread concepts
  - Verify second sandwich reuses ingredient from first
  - Verify usage_count incremented
```

---

## Prompt 8: Forager with Tiered Sources

```
Implement the forager from SPEC.md Section 3.2.1.

Reference: Sections 3.2.1, 14.2

Tasks:
1. Create prompts/curiosity.txt with template from Section 14.2

2. Create src/sandwich/sources/base.py with:
   
   class ContentSource(ABC):
       name: str
       tier: int
       rate_limit: Optional[str]  # e.g., "10/minute"
       
       @abstractmethod
       async def fetch(self, query: Optional[str] = None) -> SourceResult
       
       @abstractmethod
       async def fetch_random(self) -> SourceResult
   
   @dataclass
   class SourceResult:
       content: str
       url: Optional[str]
       title: Optional[str]
       content_type: str
       metadata: dict

3. Create src/sandwich/sources/wikipedia.py:
   - WikipediaSource implementing ContentSource
   - fetch_random(): Get random article via API
   - fetch(query): Search and return top result
   - Respect rate limit (200/minute)

4. Create src/sandwich/sources/web_search.py:
   - WebSearchSource implementing ContentSource
   - Use DuckDuckGo or similar (no API key needed)
   - fetch(query): Search and fetch top result content
   - Respect rate limit (10/minute)

5. Create src/sandwich/agent/forager.py with:
   
   @dataclass
   class ForagerConfig:
       max_patience: int = 5
       tier_1_sources: list[str]
       tier_2_sources: list[str]
       tier_3_sources: list[str]
   
   class Forager:
       current_tier: int
       consecutive_failures: int
       consecutive_successes: int
       sources: dict[int, list[ContentSource]]
       
       async def generate_curiosity(self, recent_topics: list[str]) -> str
           # Use LLM with curiosity prompt
       
       async def forage(self, curiosity: Optional[str] = None) -> ForagingResult
           # Select source based on tier
           # Fetch content
           # Log to foraging_log
           # Return result
       
       def record_success(self):
           # Reset failures, increment successes
           # Maybe increase tier if many successes
       
       def record_failure(self):
           # Increment failures, reset successes
           # Maybe decrease tier if many failures

6. Implement tier transition logic from Section 3.2.1

7. Write tests in tests/test_forager.py:

test_wikipedia_random:
  - Create WikipediaSource
  - Call fetch_random()
  - Verify returns content > 500 chars
  - Verify has URL and title

test_wikipedia_search:
  - Create WikipediaSource
  - Call fetch("squeeze theorem")
  - Verify returns relevant content
  - Verify "squeeze" or "theorem" in content

test_tier_transition_down:
  - Create forager at tier 2
  - Record 3 consecutive failures
  - Verify tier decreased to 1

test_tier_transition_up:
  - Create forager at tier 1
  - Record 5 consecutive successes
  - Verify tier increased to 2

test_rate_limiting:
  - Create WikipediaSource
  - Make rapid requests
  - Verify rate limiting delays requests appropriately

test_foraging_logged:
  - Create forager
  - Forage once
  - Verify entry in foraging_log table
```

---

## Prompt 9: State Machine

```
Implement the state machine from SPEC.md Section 5.

Reference: Sections 5.1, 5.2, 5.3, 6.4

Tasks:
1. Create src/sandwich/agent/state_machine.py with:

   class AgentState(Enum):
       IDLE = "idle"
       FORAGING = "foraging"
       PREPROCESSING = "preprocessing"
       IDENTIFYING = "identifying"
       SELECTING = "selecting"
       ASSEMBLING = "assembling"
       VALIDATING = "validating"
       STORING = "storing"
       ERROR_RECOVERY = "error_recovery"
       SESSION_END = "session_end"
   
   # Transition table from Section 5.2
   TRANSITIONS: dict[AgentState, dict[str, AgentState]]
   
   @dataclass
   class StateCheckpoint:
       checkpoint_id: UUID
       session_id: UUID
       state: AgentState
       timestamp: datetime
       data: dict  # State-specific payload
       transition_reason: str
       
       async def save(self, db: Database)
       
       @classmethod
       async def load_latest(cls, session_id: UUID, db: Database) -> Optional[StateCheckpoint]
   
   class StateMachine:
       current_state: AgentState
       session_id: UUID
       checkpoints: list[StateCheckpoint]
       
       def can_transition(self, event: str) -> bool
       
       async def transition(self, event: str, data: dict = None) -> AgentState
           # Validate transition is legal
           # Create and save checkpoint
           # Update current_state
           # Return new state
       
       async def recover_from_checkpoint(self, checkpoint: StateCheckpoint)
           # Restore state from checkpoint

2. Create src/sandwich/agent/error_handler.py with:

   async def handle_error(
       error: SandwichError,
       state_machine: StateMachine,
       session: Session
   ) -> str:
       """
       Determine next event based on error type.
       Returns the event string to trigger transition.
       """
       # Logic from Section 6.4

3. Write tests in tests/test_state_machine.py:

test_valid_transitions:
  - Start in IDLE
  - Transition through: FORAGING → PREPROCESSING → IDENTIFYING → SELECTING → ASSEMBLING → VALIDATING → STORING → IDLE
  - Verify all transitions succeed

test_invalid_transition:
  - Start in IDLE
  - Try to transition to VALIDATING directly
  - Verify raises error

test_checkpoint_persistence:
  - Create state machine
  - Make several transitions
  - Verify checkpoints saved to database
  - Verify can query checkpoints

test_crash_recovery:
  - Create state machine, transition to ASSEMBLING
  - Save checkpoint with assembler input data
  - Create new state machine
  - Load checkpoint
  - Verify state restored to ASSEMBLING
  - Verify data payload available

test_error_routing:
  - Test ContentError → routes to FORAGING
  - Test RetryableError (after max retries) → routes to FORAGING
  - Test ParseError → routes to FORAGING
  - Test FatalError → routes to SESSION_END

test_session_end_terminal:
  - Transition to SESSION_END
  - Verify no further transitions possible
```

---

## Prompt 10: Full Agent - Reuben Lives

```
Wire everything together into the main Reuben agent.

Reference: SPEC.md Sections 6.5, 8

Tasks:
1. Create src/sandwich/agent/reuben.py with:

   class Reuben:
       """The sandwich-making agent."""
       
       def __init__(
           self,
           config: SandwichConfig,
           llm: SandwichLLM,
           embeddings: EmbeddingService,
           db: Database
       ):
           self.forager = Forager(...)
           self.state_machine = StateMachine(...)
           self.corpus = SandwichCorpus(db)
           self.session: Optional[Session] = None
       
       async def start_session(self) -> Session:
           # Create session in database
           # Initialize state machine
           # Log session start
           # Return session
       
       async def run(self, max_sandwiches: int = None, max_duration: timedelta = None):
           """
           Main autonomous loop.
           Runs until patience exhausted, max reached, or shutdown requested.
           """
           self.session = await self.start_session()
           
           while not self.should_stop(max_sandwiches, max_duration):
               try:
                   await self.run_one_cycle()
               except FatalError as e:
                   await self.handle_fatal(e)
                   break
           
           await self.end_session()
       
       async def run_one_cycle(self):
           """One forage → make_sandwich cycle."""
           # Transition to FORAGING
           # Generate curiosity
           # Forage
           # Run pipeline
           # Handle result (success/failure)
           # Update patience/tier
       
       async def end_session(self):
           # Compute final stats
           # Update session record
           # Emit closing message in Reuben's voice
           # Transition to SESSION_END
       
       def emit(self, message: str):
           """Output a message in Reuben's voice."""
           # Print to console with formatting
           # Log to session

2. Add Reuben voice messages from Section 6.5:
   - On session start
   - On successful sandwich
   - On each failure type
   - On session end

3. Create src/sandwich/main.py:

   import argparse
   
   async def main():
       parser = argparse.ArgumentParser(description="Reuben makes sandwiches")
       parser.add_argument("--max-sandwiches", type=int, help="Stop after N sandwiches")
       parser.add_argument("--max-duration", type=int, help="Stop after N minutes")
       parser.add_argument("--resume", type=str, help="Resume session by ID")
       args = parser.parse_args()
       
       config = SandwichConfig()
       llm = AnthropicSandwichLLM(...)
       embeddings = OpenAIEmbeddingService(...)
       db = await Database.connect(config.database.url)
       
       reuben = Reuben(config, llm, embeddings, db)
       
       if args.resume:
           await reuben.resume_session(args.resume)
       
       await reuben.run(
           max_sandwiches=args.max_sandwiches,
           max_duration=timedelta(minutes=args.max_duration) if args.max_duration else None
       )
       
       # Print summary
       print_session_summary(reuben.session)

4. Write tests in tests/test_reuben.py:

test_session_lifecycle:
  - Start Reuben
  - Let him make 1 sandwich
  - Stop
  - Verify session created and ended in database
  - Verify session stats correct

test_three_sandwiches:
  - Configure Reuben with mock sources (return known good content)
  - Run with max_sandwiches=3
  - Verify exactly 3 sandwiches in database
  - Verify all linked to session

test_patience_exhaustion:
  - Configure Reuben with mock sources that always fail preprocessing
  - Run
  - Verify session ends after patience exhausted
  - Verify sandwiches_made = 0

test_reuben_voice:
  - Capture Reuben's emitted messages
  - Verify session start message present
  - Verify session end message present
  - Verify messages have Reuben's tone (no complaints)

test_resume_session:
  - Start session, make 1 sandwich
  - Simulate crash (just stop)
  - Create new Reuben, resume session
  - Make 1 more sandwich
  - Verify both sandwiches linked to same session

5. Manual test:
   - Run: python -m sandwich.main --max-sandwiches 3
   - Watch output
   - Verify Reuben's personality comes through
   - Verify sandwiches are sensible
   - Check database has all records
```

---

## Prompt 11: Observability Dashboard

```
Implement the observability dashboard from SPEC.md Section 8.3.

Reference: Section 8.3

Tasks:
1. Create dashboard/app.py using Streamlit:

   import streamlit as st
   
   st.set_page_config(page_title="SANDWICH Operations", layout="wide")
   
   # Auto-refresh every 5 seconds
   st_autorefresh(interval=5000)
   
   # Header with session status
   # - Current session ID
   # - Status (running/completed)
   # - Uptime
   # - Current state
   # - Current tier
   # - Patience remaining
   
   # Row 1: Key metrics
   col1, col2, col3, col4 = st.columns(4)
   # - Sandwiches today
   # - Sandwich rate
   # - Mean validity
   # - Cost per sandwich
   
   # Row 2: Charts
   col1, col2 = st.columns(2)
   # - Validity score distribution (histogram)
   # - Sandwiches over time (line chart)
   
   # Row 3: Tables
   col1, col2 = st.columns(2)
   # - Latest sandwiches (name, type, score, status)
   # - Error counts by type
   
   # Row 4: Cost breakdown
   # - Pie chart by component (forager, identifier, assembler, validator)
   
   # Row 5: Foraging stats
   # - Success rate by tier
   # - Source breakdown

2. Create dashboard/components/metrics.py:
   - Functions to query and compute metrics
   - Cache expensive queries

3. Create dashboard/components/charts.py:
   - Reusable chart components

4. Add to docker-compose.yml:
   - Streamlit service
   - Expose on port 8501

5. Test:
   - Start Reuben in one terminal: python -m sandwich.main
   - Open dashboard: streamlit run dashboard/app.py
   - Verify metrics update as sandwiches are made
   - Verify charts are readable
   - Verify error counts accurate
```

---

## Prompt 12: Analysis Engine

```
Implement the analysis engine from SPEC.md Section 10.

Reference: Sections 10.1, 10.2, 10.3, 10.4

Tasks:
1. Add cluster_id column to sandwiches table:
   ALTER TABLE sandwiches ADD COLUMN cluster_id INT;

2. Create src/sandwich/analysis/clustering.py:
   
   async def run_clustering(corpus: SandwichCorpus, config: ClusteringConfig):
       """
       Cluster sandwiches by embedding similarity.
       Updates cluster_id in database.
       """
       # Get all sandwich embeddings
       # Run HDBSCAN
       # Update cluster_id for each sandwich
       # Compute and store cluster statistics
       # Return ClusteringResult

3. Create src/sandwich/analysis/relations.py:
   
   async def detect_relations(sandwich: StoredSandwich, corpus: SandwichCorpus):
       """
       Find and store relations to existing sandwiches.
       """
       # Find similar sandwiches (embedding similarity > 0.8)
       # Find sandwiches with same bread
       # Find inverse sandwiches (bread swapped)
       # Store in sandwich_relations table

4. Create src/sandwich/analysis/ingredients.py:
   
   async def find_or_create_ingredient(
       text: str,
       ingredient_type: str,
       embedding: np.ndarray,
       sandwich_id: UUID,
       db: Database
   ) -> UUID:
       """
       Find existing ingredient by text or embedding similarity.
       Create new if not found. Increment usage if found.
       """
       # Implementation from Section 10.3

5. Create src/sandwich/analysis/metrics.py:
   
   async def compute_session_metrics(session_id: UUID) -> SessionMetrics:
       # Sandwich rate
       # Mean validity
       # Cost per sandwich
       # etc.
   
   async def compute_corpus_metrics(corpus: SandwichCorpus) -> CorpusMetrics:
       # Ingredient diversity
       # Structural coverage
       # Novelty trend
       # etc.

6. Create scripts/run_analysis.py:
   - Run clustering
   - Detect relations for recent sandwiches
   - Compute and print corpus metrics
   - Can be run as cron job

7. Write tests in tests/test_analysis.py:

test_clustering:
  - Create 10 sandwiches with varied embeddings
  - Run clustering
  - Verify cluster_ids assigned
  - Verify similar sandwiches in same cluster

test_ingredient_matching:
  - Create sandwich with bread "Bayesian prior"
  - Create another with bread "bayesian prior distribution"
  - Verify second reuses ingredient from first (fuzzy match)

test_relation_detection:
  - Create two similar sandwiches
  - Run detect_relations
  - Verify "similar" relation stored

test_metrics_computation:
  - Create session with known sandwiches
  - Compute metrics
  - Verify calculations correct

8. Run full analysis:
   - After corpus has 20+ sandwiches
   - Run scripts/run_analysis.py
   - Review cluster assignments
   - Review ingredient reuse stats
   - Verify analysis is meaningful
```

---

## Final Verification Checklist

After completing all prompts, verify:

- [ ] `docker-compose up` starts database successfully
- [ ] `python scripts/init_db.py` creates all tables
- [ ] `python scripts/seed_taxonomy.py` populates structural types
- [ ] Validator correctly separates good/bad sandwiches
- [ ] `python -m sandwich.main --max-sandwiches 5` produces 5 sandwiches
- [ ] All sandwiches have Reuben's voice in commentary
- [ ] Dashboard shows real-time metrics
- [ ] Crash recovery works (kill and resume)
- [ ] Cost tracking is accurate
- [ ] Clustering produces sensible groupings
- [ ] Ingredient reuse is detected

If all checks pass: **Reuben is alive. Let him make sandwiches.**

---

*"The prompts are complete. The path is clear. Now we build." — Not Reuben, but in his spirit*
