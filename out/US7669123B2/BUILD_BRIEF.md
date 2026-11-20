# Build brief: US7669123B2

Implement the invention in `impls/us7669123/feed_engine.py`.

## Spec (one line per claim element)
- `C1.E1` monitoring a plurality of activities in a social network environment
- `C1.E2` storing the plurality of activities in a database
- `C1.E3` generating a plurality of news items regarding one or more of the activities, wherein one or more of the news items is for presentation to one or more viewing users and relates to an activity that was performed by another user
- `C1.E4` attaching a link associated with at least one of the activities of another user to at least one of the plurality of news items where the link enables a viewing user to participate in the same activity as the another user
- `C1.E5` limiting access to the plurality of news items to a set of viewing users
- `C1.E6` displaying a news feed comprising two or more of the plurality of news items to at least one viewing user of the predetermined set of viewing users
- `C16.E1` a social network environment
- `C16.E2` a module configured to monitor a plurality of activities in a social network environment
- `C16.E3` a storage medium for storing the plurality of activities in a database
- `C16.E4` a module configured to generate a plurality of news items regarding one or more of the activities, wherein one or more of the news items is for presentation to one or more viewing users and relates to an activity that was performed by another user
- `C16.E5` a link component configured to attach a link associated with at least one of the activities of another user to at least one of the plurality of news items where the link enables a viewing user to participate in the same activity as the another user
- `C16.E6` a privacy component configured to limit access to the plurality of news items to a set of viewing users
- `C16.E7` a media generator configured to display a news feed comprising two or more of the plurality of news items to at least one viewing user of the predetermined set of viewing users

## Rules
- Decorate each implementing function with `@implements("<element id>", ...)` and give it a docstring
  describing what it does in the claim's own terms.
- Register at least one behavioural `@check("<element id>")` per element that exercises the real code.
- Done means both commands exit 0:
    NECRO_IMPL=impls.us7669123.feed_engine pytest out/US7669123B2/evals
    python -m necro judge US7669123B2 --impl impls.us7669123.feed_engine
- Do not edit the generated evals. A generic CRUD app will not pass the judge.
