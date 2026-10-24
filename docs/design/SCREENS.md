# Inter Club Portal - Screen Generation Matrix (Stitch MCP)

## Design Checklist (Part G)

1. Every element traces to a PRD ID, and nothing from Part C's 'not drawn' list appears. **[Yes]**
2. Only the Part B2 colours are used; the logo sits on white. **[Yes]**
3. Text and control contrast meet Part B10; status is never shown by colour alone. **[Yes]**
4. Works at 360 px: no sideways page scroll (except availability grid), touch targets >=44 px. **[Yes]**
5. Toggle switch appears only for user Active or Inactive. **[Yes]**
6. Role rules visible: Lead never sees Approve/Reject, Assignee list scoped, etc. **[Yes]**
7. None of the Part B8 'do not use' items appear. Copy follows B9. **[Yes]**
8. Placeholder content is realistic and consistent between screens. **[Yes]**

## Screen Mapping

| Screen | Route | Device | Stitch Screen ID | PRD Trace | Status |
|--------|-------|--------|-----------------|-----------|--------|
| Login | /admin/login | Desktop | 0bc9004979e7423fbc06007a3ed8a5fc | AUTH-01 | PASS |
| Login | /admin/login | Mobile | 26b6120ab0b94711b2b324866edc2bea | AUTH-01 | PASS |
| First Login | /admin/first-login | Desktop | 47f01ee90c0642208a95ef7814c2148a | AUTH-04 | PASS |
| First Login | /admin/first-login | Mobile | dc6fd25cccf24e13acf69cb695d2f1ac | AUTH-04 | PASS |
| Profile | /admin/profile | Desktop | 3b8f1c1837044df3b05c2dac60d50075 | Section 13 | PASS |
| Profile | /admin/profile | Mobile | ff04826e94bf46a8ac883dd70750f960 | Section 13 | PASS |
| Admin Dashboard | /admin | Desktop | f35cb8c78e0a430dac19dc4603f8d30e | AV-01, TK-10 | PASS |
| Admin Dashboard | /admin | Mobile | 50efcb41c8b244038ca1c9f443cd2d1f | AV-01, TK-10 | PASS |
| Lead Dashboard | /admin | Desktop | 1e9b72d1387b4dc8a9e5e6d3c8dc1829 | AV-01, TK-04 | PASS |
| Lead Dashboard | /admin | Mobile | d242879b4f964128afc03fea0142aa98 | AV-01, TK-04 | PASS |
| User Dashboard | /admin | Desktop | 9ffa7d855cc640168ee10ac7d10d0547 | TT-01, TK-04 | PASS |
| User Dashboard | /admin | Mobile | 79966e32b9d8466e96fe4973abaf22c0 | TT-01, TK-04 | PASS |
| Users | /admin/users | Desktop | 698b954a31e74c6aba3a272eab292994 | AUTH-03, AUTH-05 | PASS |
| Users | /admin/users | Mobile | 5cc663ba9c3a42fcbc7741adefc6c44b | AUTH-03, AUTH-05 | PASS |
| Teams | /admin/teams | Desktop | d92f733208994e75bd1daab669faa643 | TEAM-01 | PASS |
| Teams | /admin/teams | Mobile | 63b5a8f440fe4b97aacbf1876f81f7cd | TEAM-01 | PASS |
| My Timetable | /admin/timetable | Desktop | ebd57ae667d442eeb1ceed9cc5aaa1b4 | TT-01, TT-05 | PASS |
| My Timetable | /admin/timetable | Mobile | b7ae8ff619b24be2a943de9947190cf0 | TT-01, TT-05 | PASS |
| Availability | /admin/availability | Desktop | 128ea01c8bf040e2857320c78f5f3029 | AV-01, AV-04 | PASS |
| Availability | /admin/availability | Mobile | 0730837107f84ce3abadf76a6d9642a7 | AV-01, AV-04 | PASS |
| Tasks | /admin/tasks | Desktop | 77f34a821c374629872236dcf0bcc0e6 | TK-01, TK-06 | PASS |
| Tasks | /admin/tasks | Mobile | 94634d93943849a993f0361522a11e0b | TK-01, TK-06 | PASS |
| Review queue | /admin/review | Desktop | 8d3a3b45f06a46f68c89b22d3bd6387e | TK-05, TK-10 | PASS |
| Review queue | /admin/review | Mobile | d1cb7f3f62a44a24b88f9a90d53053a9 | TK-05, TK-10 | PASS |
| Events | /admin/events | Desktop | 77c24af252fa4a0c9e9012d87c169507 | EV-01, EV-08 | PASS |
| Events | /admin/events | Mobile | 9303ffa006394be18075e56fac6868ef | EV-01, EV-08 | PASS |
| Access Denied | System | Desktop | 145024339d2a484c827b9d672a0b4720 | AUTH-07 | PASS |
| Access Denied | System | Mobile | 68f679570fc64438b940189c816751ee | AUTH-07 | PASS |
| Not Found | System | Desktop | 50b084c9b3874b9e8270be59ab4479f6 | System | PASS |
| Not Found | System | Mobile | 9d710030eab74b57915cf8df6ef0d6d2 | System | PASS |

## Needs my OK (Exceptions List)
1. Sign out in the menu.
2. A confirm-password field and the helper “At least 12 characters”.
3. Priority options (Low, Medium, High).
4. Team field is hidden when the new user's role is Admin on the Users sheet.
5. Day list in Availability defaults to standard work week.
6. Pagination on the Users and Tasks tables.
7. Email, role and team shown read-only on Profile.
8. Upload size limit text references abstract 5MB constraints.
9. Saved timetable displays as functional columns.
