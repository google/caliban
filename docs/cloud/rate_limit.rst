Rate Limiting
^^^^^^^^^^^^^

``caliban cloud`` relies on AI Platform for rate limiting, so you can submit many,
many jobs using an ``--experiment_config`` (up to ~1500 total, I believe?) and AI
Platform will throttle submissions to the default limit of 60 submissions per
minute. If your project's been granted higher quotas, you won't be throttled
until you hit your project's rate limit.

Job submission on Cloud presents a nice progress bar, with terminal colors and
more. The log commands, URLs, jobIds and custom arguments are highlighted so
it's clear which jobs are going through. On a failure the error message prints
in red.
