---
doc_id: gen-services
title: "Saudi health services, apps, insurance checks and complaints"
category: general
entity: "Saudi health system"
default_confidence: TYPICAL
last_verified: 2026-09-28
review_by: 2027-09-28
language: en
sources:
  - name: "WHO EMRO - Saudi Arabia remote health services (app descriptions)"
    url: "https://www.emro.who.int/noncommunicable-diseases/highlights/saudi-arabia-remote-health-services-provision-during-the-covid-19-pandemic.html"
  - name: "PMC - 937 call centre and MOH apps"
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8764273/"
  - name: "Saudipedia - 937 Health Center"
    url: "https://saudipedia.com/en/937-health-center"
  - name: "National Platform - Healthcare"
    url: "https://my.gov.sa/en/content/health-care"
  - name: "National Platform - Complaint against a health care provider"
    url: "https://my.gov.sa/en/services/484584"
  - name: "Council of Health Insurance portal (Insurance Authority transfer notice)"
    url: "https://www.chi.gov.sa/en/Pages/default.aspx"
  - name: "GGI complaints page (regulator contact numbers)"
    url: "https://www.ggi-sa.com/en/page/Complaints"
  - name: "Expat Focus - health insurance in Saudi Arabia"
    url: "https://www.expatfocus.com/saudi-arabia/guide/saudi-arabia-health-insurance"
  - name: "Truescho - health insurance for expats 2026"
    url: "https://truescho.com/en/blog/health-insurance-expats-saudi-arabia-2026"
---
# Saudi health services, apps, insurance checks and complaints

## Sehhaty app
Sehhaty is the Ministry of Health's health app. It supports tele-consultations, appointment booking at primary healthcare centres, electronic prescriptions, pharmacy search, electronic sick leave, vital-sign tracking and activity tracking. `[TYPICAL]` Feature lists come from 2020 to 2023 descriptions, so confirm current features in the app.
Questions this answers: What is Sehhaty? How do I get a sick leave electronically? Can I see a doctor online in Saudi Arabia?

## Mawid appointment app
Mawid is the Ministry of Health's national appointment gateway, launched in 2018. It lets users book, reschedule and cancel appointments at Ministry primary healthcare centres and referral services. `[TYPICAL]` It is separate from this clinic assistant: this assistant manages this clinic's own bookings only. `[DEMO_CONFIG]`
Questions this answers: How do I book an appointment on Mawid? Can I cancel a Mawid appointment? What is Mawid?

## Wasfaty and prescription refills
Wasfaty is the app that connects patients to a network of pharmacies for filling prescriptions and refilling medication, integrated with primary healthcare centres and other facilities. `[TYPICAL]`
Questions this answers: Which app can refill my prescription? What is Wasfaty?

## Seha virtual consultations
The Seha app connects users to general practitioners and specialists for teleconsultation by video, text or voice. `[TYPICAL]`
Questions this answers: Is there a virtual hospital app in Saudi Arabia? Can I get a video consultation?

## Government hospitals, citizens and expatriates
Healthcare in government medical facilities is provided free of charge to Saudi citizens. `[OFFICIAL]` Expatriate residents are legally required to hold CHI-compliant health insurance, so non-urgent care is generally paid through their insurance. `[TYPICAL]` Insured expats mostly use private hospitals in their insurer's network. `[TYPICAL]`
Questions this answers: Is healthcare free in Saudi Arabia? Do expats need insurance? Can expats use government hospitals?

## Checking your active insurance policy
The CHI Insurance Information Inquiry e-service lets a beneficiary look up active policy details, the insurer and the network. `[TYPICAL]` The insurance card and HR-provided policy documents show the network tier and covered facilities. Visiting a facility outside the network can leave the patient responsible for the full cost. `[TYPICAL]`
Questions this answers: How do I check whether my insurance is active? How do I know which hospitals my insurance covers?

## How to complain about an insurance company or a provider
First complain to the insurer, which is expected to respond within about 15 business days. `[TYPICAL]` If unresolved, escalate: since 2024 complaints against insurers and third-party administrators are handled by the Insurance Authority (customer care 8001240551, website care.ia.gov.sa). `[OFFICIAL]` Complaints about a healthcare provider can be filed on the CHI portal after logging in through Nafath, and the complainant must hold valid health insurance. `[OFFICIAL]` An older CCHI number, 920001177, appears on some insurer pages and may be outdated. `[VARIES]`
Questions this answers: How do I complain about my insurer? Who regulates health insurance complaints? How do I complain about a hospital or clinic?

## What to bring to a medical visit
Bring your Iqama or national ID and your insurance card. `[TYPICAL]` Bring previous reports or prescriptions relevant to the visit and arrive early for check-in. `[DEMO_CONFIG]` Specific preparation for tests (such as fasting) depends on the appointment type and is covered in the preparation-instructions knowledge base.
Questions this answers: What documents do I need for my appointment? Do I need my insurance card?
