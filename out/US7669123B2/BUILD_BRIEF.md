# Build brief: US7669123B2

Implement the invention in `impls/us7669123/feed_engine.py`.

## Spec (one line per claim element)
- `C1.E1` monitoring a plurality of activities in a social network environment
- `C1.E2` storing the plurality of activities in a database
- `C1.E3` generating a plurality of news items regarding the activities associated with a user of the social network environment
- `C1.E4` attaching an informational link associated with at least one of the activities to at least one of the news items, the informational link enabling a viewing user to participate in the same activity
- `C1.E5` limiting access to the plurality of news items to a predetermined set of viewing users
- `C1.E6` assigning an order to the plurality of news items
- `C1.E7` displaying a news feed comprising two or more of the plurality of news items to at least one viewing user of the predetermined set of viewing users
- `C16.E1` a monitoring module configured to monitor a plurality of activities in the social network environment
- `C16.E2` a database configured to store the plurality of activities
- `C16.E3` a news item generator configured to generate a plurality of news items regarding the activities associated with a user
- `C16.E4` a link component configured to attach an informational link to at least one of the news items enabling a viewing user to participate in the same activity
- `C16.E5` a privacy component configured to limit access to the plurality of news items to a predetermined set of viewing users and to assign an order to the news items
- `C16.E6` a media generator configured to display a news feed comprising two or more of the plurality of news items to at least one viewing user

## Rules
- Decorate each implementing function with `@implements("<element id>", ...)` and give it a docstring
  describing what it does in the claim's own terms.
- Register at least one behavioural `@check("<element id>")` per element that exercises the real code.
- Done means both commands exit 0:
    NECRO_IMPL=impls.us7669123.feed_engine pytest out/US7669123B2/evals
    python -m necro judge US7669123B2 --impl impls.us7669123.feed_engine
- Do not edit the generated evals. A generic CRUD app will not pass the judge.
