# Bonus — Judgment Challenge

The brief does not attribute a specific unsafe instruction to a senior leader. I would challenge this hypothetical extension of its delivery deadline: **“Put the 48-hour demo in front of real patients immediately; we can add individual login and concurrency protection later.”**

I would accept the need to demonstrate value quickly and deliver a working end-to-end booking experience. I would change the release scope: demonstrate the assistant with synthetic records in a restricted environment, rather than describe it as ready for real patient operations.

I would explain: “We can demonstrate the workflow on time. However, the current login shares one demo patient, and simultaneous requests are not fully coordinated. Using real records now could expose the wrong patient's information or create conflicting bookings. I recommend keeping today's demonstration synthetic while we complete the controls needed for a patient pilot.”

Before that pilot, I would prioritize OTP login linked to each patient's own records, database-backed concurrency controls, and an authenticated doctor-side workflow for maintaining valid schedules. Approval-required changes would remain blocked unless a real staff process exists. The assistant must not claim it contacted staff or completed a change without evidence.

To preserve speed, I would keep the existing frontend, Python workflow, database and retrieval approach. I would avoid a platform rewrite, agree a small release checklist with the leader, and demonstrate progress using cross-patient access tests, simultaneous-booking tests and the existing evaluation cases. A controlled synthetic demo delivers immediate evidence; a limited patient pilot follows once the essential controls pass.

This protects Apex's credibility while preserving the deadline's purpose: showing a useful, defensible solution rather than promising production readiness that has not been established.
