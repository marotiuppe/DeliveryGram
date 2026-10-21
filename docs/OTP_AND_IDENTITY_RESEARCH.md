# OTP and identity for rural users

Date: 2026-10-20. Prices come from third-party pages and disagree with each other; confirm on the official pages before budgeting.

## Bottom line
- **There is no free OTP at scale.** WhatsApp, SMS and Firebase phone auth all charge per message or need paid setup.
- **Many of our users won't have WhatsApp, email or a smartphone**, so any OTP channel excludes some of them. Do not make OTP the only way in.
- **Design: identity = phone number, proven in the cheapest way available for each user**, with assisted registration by shopkeepers and village agents. Use OTP only where it is free or cheap.

## Options checked
| Option | Cost | Setup | Reaches feature-phone users? | Verdict |
|---|---|---|---|---|
| **Email OTP** | Free (SMTP) | Trivial | No (few villagers have email) | Use now for admin/staff and email-holders |
| **WhatsApp Cloud API, OTP template (Meta)** | About INR 0.11-0.13 per delivered message (third-party figures; Meta rate card not confirmed). Billing is per delivered template message since 1 July 2025 | Meta business verification, approved sender number, template approval | No (needs WhatsApp) | Cheap, but not free. Later option |
| **WhatsApp "customer sends us a message" verification** | Free if replies stay inside the customer-initiated service window (verify current Meta terms) | Same Meta setup; webhook | No (needs WhatsApp) | Best free option for WhatsApp users: the customer taps "Verify on WhatsApp", sends a pre-filled code, our webhook reads their number. No template cost |
| **SMS OTP (India)** | About INR 0.10-0.18 per SMS via an aggregator | TRAI DLT registration (entity, sender ID, template approval; fees quoted from free to about INR 5,900 plus GST) | Yes (any phone) | Works for everyone but paid and paperwork heavy |
| **Firebase phone auth** | Needs the Blaze (billing) plan; first 10 SMS/day free; India price quoted at about USD 0.07 per SMS in one source (older sources differ) | Google Cloud billing | Yes | Not free; skip |
| **Voice OTP / missed-call verification / IVR** | Not found; vendor quotes needed | Telephony provider | Yes, including basic phones | Good fallback for feature phones. One vendor estimates 15-25% of calls fail to connect (DND, call blockers) |

## Recommended approach
1. **Assisted registration (free, works for everyone).** A shopkeeper or village agent ("Sahayak") registers the customer's phone number and sets a temporary 4-digit PIN. The customer logs in with phone + PIN and must change the PIN on first login. No OTP needed. Staff can reset forgotten PINs.
2. **Phone and WhatsApp orders entered by staff.** The operator places the order for a phone number. The customer needs no account, app or smartphone.
3. **Email OTP** now for admin, staff and anyone with an email.
4. **WhatsApp verification** (customer-initiated, free) when we set up Meta. SMS or voice OTP only if we need it for phone-only users and can fund it.
5. **Delivery OTP: do not use SMS OTP at delivery.** Use a 4-digit **delivery code** instead:
   - shown in the customer's order screen, told by the operator on the phone, or written on the bill slip in the parcel;
   - **required** for UPI/prepaid orders, medicines and orders above a value threshold (default INR 2,000);
   - **skipped** for small COD orders, where handing over cash is the confirmation.

## Risks
- A 4-digit PIN is weak against guessing, so logins lock for 15 minutes after 5 wrong attempts.
- Staff-set PINs mean staff briefly know customer PINs; forced change on first login limits this.
- Check Meta's terms for the free service window and Meta's current rate card before relying on the WhatsApp figures.

## Sources
- WhatsApp pricing (third-party summaries, Meta page not read): https://www.authgear.com/post/whatsapp-api-pricing and https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing
- Firebase phone auth: https://magora-systems.com/firebase-pricing/ and https://blog.logto.io/it/firebase-authentication-pricing
- India SMS and DLT: https://www.telerivet.com/blog/india-sms-compliance-trai-dlt-registration-and-tcccpr-guide and https://www.sent.dm/en/resources/sms-pricing/india-sms-pricing
- Voice OTP and missed call: https://exotel.com/glossary/voice-otp-missed-call-authentication/ and https://www.hillteck.com/blog/cod-verification-ivr-vs-whatsapp.html
