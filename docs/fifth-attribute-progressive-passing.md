# Fifth attribute: Line Breaking — Progressive Passing Proxy

This integration includes Joseph's Level A method as a supported measurement
candidate for the fifth attribute. It does not claim verified opponent-line
breaks. All numeric rating previews are **PRIVATE / EXPERIMENTAL**, isolated in
`data/derived/fifth-attribute-private-v1/`, with no production delivery or website
export. Version: `joseph-level-a-player-season/v1`.

## Reused implementation and added integration

The latest local `Joseph-dev` is `013c8edd5196a15ac826558f4b0964cc6f3a3e58`.
Its `src/metrics/line_breaking.py` Level A preparation, flags and counts already
exist in `src/metrics/progressive_passes.py`. `src/passing.py` already adds stable
identity, accounting, explicit whole-cohort calibration and supported-minute
rates. AST parity tests compare the original functions directly. Joseph remains
the original progressive-passing method contributor. No branch merge or method
duplication was needed.

Added `src/fifth_attribute.py` combines disjoint verified raw observations across
clubs into one canonical player-season. `scripts/prepare_fifth_attribute.py`
reads the existing sealed reconstruction, final independent verification and
separate 34-match Bundesliga evidence. It adds measurable open-play pass sample
sizes, difficulty diagnostics, missingness, and a separate private FIFA preview.
`scripts/assess_fifth_attribute.py` measures descriptive stability and sensitivity.
There is no source acquisition, exposure reconstruction, Parquet writer or
frontend change in this integration.

## Measurement and scope

Joseph's unchanged rules: open-play passes exclude set pieces, Unknown and Injury
Clearance outcomes. A progressive attempt moves at least 10 yards forward and
reduces Euclidean distance to the centre of the goal by at least 25%. A successful
progressive pass additionally has an absent outcome. Third-crossing is a separate
subset ending in a higher third, at x=40/80. Incomplete-pass endpoints describe
where the ball ended, not an invented intended destination.

Every match's progressive UUID sets and counts must equal the sealed source
measurements. Four-league independent counts and exact elapsed seconds must also
agree. Every measured pass must have the canonical source actor, valid geometry,
and lie inside supported exposure. Failed appearances remain enumerated and
never become zero. Supported zero-pass appearances can contribute zero with
known positive minutes; zero progressive attempts yield a missing completion
percentage. Rates describe exactly the retained supported match IDs.

The pending undelivered fixture 3879594 is retained as explicit missingness and
excluded from calibration and reference candidacy. No 360 data is required or
used. Full player-season coverage is never inferred from observed fixtures.

Difficulty uses the existing formula `(d_start-d_end)*(1-p_hat)` for successful
progressive passes, where p_hat is completion rate by league-season, starting
third and length band [0,15), [15,30), [30,infinity). Calibration includes **all
measurable open-play passes from all actors and positions** in the explicitly
named eligible four-league observed fixture cohort. The artifact records exact
cohort sizes, cells and input hashes. Completeness is relative to that named
observed cohort, not certification of an entire league season. Bundesliga has no
difficulty calibration; its value is missing. A transfer involving Bundesliga
therefore has no combined difficulty value, while its raw progressive counts
and aligned minutes remain combinable.

One player-season gets one future card. Raw counts and exact minutes are summed;
club rates and ratings are never averaged. The most-played verified fine
position group wins, then DM/CM maps to MID. CB stays separate; unresolved ties
receive no comparison group. All other observed positions remain visible.

## Headline recommendation and private reference policy

Recommend **successful progressive passes per 90**. It is an interpretable count
rate, preserves Joseph's geometry definition and can support Bundesliga's
limited observations without estimating a league-season difficulty model. Keep
completion percentage, attempts, third-crossing rate, measured pass count and
difficulty value as diagnostics. Difficulty value additionally depends on cell
sample size, distance gained, and the observed league calibration mix.

This recommendation is not a claim of established cross-league or positional
fairness. MID/CB separation only partially controls role differences. Possession,
team style and observed-fixture selection can affect both metrics. The separate
assessment compares alternating fixture subsets, metric rank agreement, league
summaries and >=900 versus >=1800 minute populations. These are descriptive
checks, not an out-of-sample validation or correction for incomplete coverage.
Approval of population composition and statistical suitability remains pending.

The private preview selects unique player-seasons with every observed appearance
supported, >=900 combined verified minutes, a unique dominant MID or CB group,
only four-league contributions and no pending fixture. Bundesliga contributors
cannot enter either reference pool, including transfers. No real production
reference membership is granted. The versioned artifact stores exact member IDs,
n, mean and **sample** standard deviation separately for MID and CB.

`z=(x-mean)/sample_std_dev`; `rating=clip(65+10*z,1,99)`, without an invented
scale or rounding rule. Undefined or zero-variance pools yield no score. Private
projections outside the reference population retain minutes, low-minute status,
subset status and Bundesliga labels. They are not production scores or approved
comparisons. Production-shaped measurement rows retain `rating: null`.

## Website work remaining

1. Record formal approval of the proxy label, headline metric, individual FIFA
   formula and precise reference population; accept the documented source,
   elapsed-minute and observed-fixture scope evidence. The latest transfer and
   dominant-position policy is implemented here; it is not reopened as a new
   question. Any remaining official admission records must reflect that policy.
2. Admit approved evidence and population through the existing scoring gates.
   Keep incomplete Bundesliga observations separate from reference membership.
   Current scoring admission is unchanged; private previews cannot bypass it.
3. Add an approved backend delivery adapter carrying this proxy's value, sample,
   minutes, coverage and missingness into `line_breaking_passes`. Existing
   `src/provisional_delivery.py` explicitly forbids fifth-attribute observations;
   update that contract and its tests only under the eventual approved policy.
4. Wire the website's fifth card attribute to the approved adapter; show
   “Progressive Passing Proxy”, diagnostics, N/A reasons and Bundesliga LIMITED
   DATA. Preserve one card per player-season. This task leaves all existing
   frontend changes untouched. Any OVR or archetype incorporation still follows
   its own existing admission and approval rules.

## Reproduction

```powershell
python -B -m scripts.prepare_fifth_attribute --output data/derived/fifth-attribute-private-v1
python -B -m scripts.assess_fifth_attribute --input data/derived/fifth-attribute-private-v1
python -B -m scripts.validate_fifth_attribute --input data/derived/fifth-attribute-private-v1 --output data/validation/fifth-attribute-tests-v1/package-validation.json --tests data/validation/fifth-attribute-tests-v1/results-final.xml
```

The generator requires a new output directory and refuses overwrite. To repeat,
choose another private output directory. Source evidence is byte-bound and read
only. Outputs include player measurements, match observations, fixture audit,
calibration cells, private previews and a manifest binding inputs and code.
The final validator also checks reversed-input determinism, conservation,
source and code hashes, protected Parquet hashes, production-contract rejection,
and the complete regression XML. It requires a new validation output file.
