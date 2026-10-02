---
doc_id: clinic-policies
title: "Clinic assistant policies (demo configuration)"
category: clinic_policy
entity: "Demo clinic"
default_confidence: DEMO_CONFIG
last_verified: 2026-09-28
review_by: 2027-09-28
language: en
sources:
  - name: "Booking workflow documentation (booking-workflow.md), design decisions and assumptions"
---
# Clinic assistant policies (demo configuration)

These are demo policies taken from the booking workflow design. They are configuration for this assessment, not real clinic policy, and must be replaced with the clinic's own rules in production.

## How patients can book an appointment
A patient can book by doctor name, by specialty (the assistant lists matching doctors and their availability), by describing a reason that the assistant softly maps to a specialty suggestion, by returning to a doctor they saw before, or by scheduling a follow-up their doctor has already created. `[DEMO_CONFIG]` The assistant checks both the doctor's availability and the patient's own existing appointments before confirming. `[DEMO_CONFIG]`
Questions this answers: How can I book an appointment? Can I book by doctor name? Can I book by specialty? Can I book with the same doctor again?

## Cancellation and rescheduling policy
Cancellations more than 24 hours before the appointment are processed automatically. Cancellations within 24 hours need human approval, so the assistant hands them to a team member. `[DEMO_CONFIG]` The same 24-hour rule is applied to rescheduling as a design assumption. `[DEMO_CONFIG]` The demo defines no cancellation fee or no-show penalty, so the assistant must not state one.
Questions this answers: Can I cancel my appointment? What if I cancel within 24 hours? Is there a cancellation fee? Can I reschedule at short notice?

## Follow-up appointments
When a doctor recommends a follow-up, it appears for the patient as an unscheduled follow-up linked to the original visit. The patient chooses their own date and time from the doctor's available slots. `[DEMO_CONFIG]`
Questions this answers: How do I book a follow-up? My doctor asked me to come back, what do I do?

## How far ahead appointments can be booked
Availability is shown for up to 90 days ahead, and slots that overlap a doctor's leave are hidden. `[DEMO_CONFIG]` The 90-day window is a configurable default, not a clinic rule.
Questions this answers: How far in advance can I book? Why are some dates not available?

## Identity and privacy
The assistant only shows or changes appointments belonging to the verified session's patient. It never accepts a patient ID typed into the chat and never shares another patient's details. `[DEMO_CONFIG]` Full phone-number and one-time-passcode verification is planned for production. `[DEMO_CONFIG]`
Questions this answers: Can I see my family member's appointments? How do you verify who I am?

## What the assistant will not do
The assistant does not diagnose, recommend treatment or give clinical advice, apart from the standard first-aid steps in the first-aid guide during an emergency. It does not confirm what a specific patient's own insurance policy will pay: it can explain typical coverage and direct the patient to their policy document or insurer. It never confirms a booking, cancellation or reschedule unless the system has actually confirmed it. `[DEMO_CONFIG]`
Questions this answers: Can you tell me if my insurance covers this? Can you diagnose my symptoms?

## When the assistant hands over to a human
The assistant escalates when the request stays ambiguous after clarification, a system action fails or times out, the patient asks for a person, the request involves another person's information, a cancellation falls inside 24 hours, or the patient describes an emergency. `[DEMO_CONFIG]`
Questions this answers: How do I talk to a human? When will the assistant transfer me?

## Clinic opening hours and contact details
The demo configuration does not define clinic opening hours, address or phone number. The assistant must say it does not have this confirmed and offer to hand over to a team member rather than guess. `[DEMO_CONFIG]`
Questions this answers: What are your opening hours? Where is the clinic? What is the clinic phone number?
