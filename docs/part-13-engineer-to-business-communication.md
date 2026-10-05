# Part 13 — Engineer-to-Business Communication

The assistant relies on an AI service. If that service goes down, it may temporarily be unable to understand a request or answer a question. It can also misunderstand what someone means or produce an incorrect answer that sounds convincing—sometimes called a “hallucination.” Without checks, this could mislead a patient about an appointment or insurance coverage, so we cannot promise perfect responses.

We manage reliability by checking appointment details against the booking system, asking patients to confirm changes, and keeping clinic rules outside the AI's control. Knowledge answers use the supplied reference material and show their sources. If there is not enough information, the assistant should say so rather than guess. These checks reduce mistakes, but a source can still be outdated or a question misunderstood. We test booking and failure scenarios, and a production service would also need ongoing monitoring and review of reported errors.

Some decisions need a person. For example, cancelling **30 minutes before an appointment** may affect the doctor's schedule and require an exception to clinic policy. With the current 24-hour notice rule, the assistant stops the automated cancellation and explains that staff approval is required. The same boundary applies to rescheduling under the current settings.

In this demo, the appointment stays unchanged and **no request is automatically sent to staff**; the patient must contact the clinic through its usual channel. A future escalation feature would send a tracked request to authorized staff and report its actual outcome. The assistant must never tell a patient that an appointment was changed or a staff member was contacted unless that really happened.
