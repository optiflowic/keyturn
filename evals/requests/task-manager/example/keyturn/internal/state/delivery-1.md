# Task state: delivery-1

- Task: delivery-1
- Requirements version: 2
- Branch: `task/delivery-1`
- Status: done
- Current step: none
- Stopped because: none
- Can continue: not applicable
- Rework: 1 of 3
- Updated: 2026-11-09T09:12Z

## Summary

Delivery 1 is done: the client accepted it, and the pull request is merged. The task stopped four times on the way, for the client's answers, for a usage limit, for the maintainer's decision on a design answer that could not be built, and for the client's acceptance, and was resumed each time.

## Steps

| Step | Status | Output | Commit | Notes |
|---|---|---|---|---|
| spec | done | [requirements](../../client/requirements.md), [approvals](../../client/approvals.md), [decision card 3](../../client/decision-card-3.md) | `1f3d2b8` | approved in Japanese, version 1 with decision card 3 (the look, left to us), then version 2 (username sign-in) |
| design | done | [design](../design.md), [threat model](../threat-model.md), [ADRs](../adr/), [design summary](../../client/design-summary.md) | `a51f0c2` | decision cards 1 and 2 answered |
| conventions | done | [conventions](../conventions.md), linter configs | `b7e4410` | |
| implement | done | [handoff](../handoff.md) | `9b02d4f` | second round, after review F-1 and F-2 and security review F-1 to F-3 |
| qa | done | [test report](../test-report.md) | `d2a7f13` | tested `9b02d4f` |
| security-review | done | [security review](../security-review.md) | `e5b8c90` | reviewed `09f4c3d`..`9b02d4f` |
| review | done | [review](../review.md) | `f1c4d27` | reviewed `09f4c3d`..`9b02d4f` |
| deliver | done | [acceptance guide](../../client/acceptance-guide.md), [delivery report](../../client/delivery-report.md) | `c08d5e1` | |
| merge | done | [approvals](../../client/approvals.md) | `5e9b3c7` | accepted by the client on 2026-11-09 |

## Commits

- `0b7c1e4d6ad4dc4629c826f98e63e071bf211b6b`: deliver, round 1
- `0d2e5f81565bed2e65d0fe4cee992d011109b30f`: spec, round 1
- `0e6a3b9c33d58aeca742d5316b9189c3fc351413`: spec, round 1
- `1a4f7c2cb66820f0c8bde7975fbd7836b7a3d1a5`: spec, round 1
- `1f3d2b8e5b75ce3bc4c423479b8aa9aafecfaf19`: spec, round 1
- `2a9c4d11495a29783a08f4a65dcdc82c9a21e262`: deliver, round 1
- `3c8f1a6e3f595e594667468b98ae073cfc9bbb74`: design, round 1
- `7c9e011ba1d0a28528367d30023493f21b7f8f6c`: deliver, round 1
- `5d0b9e2fb4b1acd5d12d215a84bb0e366c210e15`: design, round 1
- `7e1a2b55cf35c0230202752ef3e44e5512ba405a`: deliver, round 1
- `a51f0c27e759f74e2ce038fe33bff98d285bd039`: design, round 1
- `ab3e9d68c05186c1aaabec3c4e28c8729257e8a1`: deliver, round 1
- `b7e44103f31bad9654d8e75f3a7bc30708f7732d`: conventions, round 1
- `c2e6a9490d77165021aa86ad78556983eb42de92`: deliver, round 1
- `3d5e7a1464974925b6d36c0104ff54f817f8f2bd`: implement, round 1
- `4e1c9a75e25b5e94e200599714f3b855cd7c4c22`: implement, round 1
- `6e18997125df73c7be7998fe47bf797c8ebc7ba0`: deliver, round 1
- `d84e81c3f598897b69a45b472eb69ee64e3e5559`: answer, round 1
- `4f8d2c048a5ca20a1469a5e98387bdc338417e4d`: deliver, round 1
- `5b2f0d65d6fd8b86aa42edab9110de5903a026b8`: deliver, round 1
- `6a8c3e210e24fe5f5793f2ec500b689f3ac58271`: implement, round 1
- `3dfa36745d867681819f40571506b7e8c62a99d2`: deliver, round 1
- `4f17fcddc6af5215c8acef7a4e31ef39a017d74f`: deliver, round 1
- `30cd9d743a2364309b0674a1649700da9f3d2920`: deliver, round 1
- `5edff8c36286afc3d35f223ae3dc297dee70663a`: deliver, round 1
- `2c1f895d852b216dc7db9ca16a2ae9e65110d2b0`: answer, round 1
- `1decb7060c5324c0b65228d1ccd4d14d253c59c2`: deliver, round 1
- `6c59abc441c0748a9a86188ab68fe00076993433`: implement, round 1
- `7d4b1f9f7577a107f473c1557c5d3de9d3e2dab4`: deliver, round 1
- `8c6e2a0fc2d2a775078e05ad3448b1d09362d0e4`: qa, round 1
- `8f0a5b360eedb61015f04ba6fbd34092981e8636`: deliver, round 1
- `91b7d4ce2d611b37e3c581faac49f69d66d24776`: security-review, round 1
- `93e2c6a83f8bbfce6579d4e8d63a5f6d139616e1`: deliver, round 1
- `95a1f8e0b28bc195127ae60f514ecadb3069ed06`: review, round 1
- `97c3b0d68ba9b979a2882d0b003e37fb9d03a507`: deliver, round 1
- `9b02d4f5578b6d06fb14427a6e353504a7d463ae`: implement, round 2
- `a0d6e3fde8adcaac2c8ff5872ec4abab8a31888c`: deliver, round 2
- `d2a7f131478c6414ddc250609295e366a47021cc`: qa, round 2
- `d4f1a7c76fd4900687c282f8b8c67f5092a27778`: deliver, round 2
- `e5b8c9062b5f783836273c5995b60d7130522ab6`: security-review, round 2
- `e7c2d910cb28fa61c1d96ae3f8994d148ff171f2`: deliver, round 2
- `f1c4d27f7563f6335310bf7da5b2d8787e173d0d`: review, round 2
- `f3a8e05f617c0b829d27d118e9969905328193c3`: deliver, round 2
- `c08d5e18368f08616c7e7b4b37e9dfdc8eafe711`: deliver, round 2
- `b4d7e2a09c3f61e85a2d4c7b9e0f1a3d5c6b8e27`: deliver, round 2
- `2f6a9d1c4e8b07a3d5f2c9e6b1a4d7c0e3f8b562`: merge, round 2
- `6c1e8f3a5d2b9047e6c3a8f1d5b2e9c7a4f0d318`: deliver, round 2
- `8a3f5c2e9d1b4706f8e2a5c3d9b1e7f4a6c0d285`: deliver, round 2
- `5e9b3c7d1a4f28e6b0c9d3a7f5e1b8c2d6a4f093`: merge, round 2

## Open questions

None.

## History

- 2026-11-08T01:05Z: started
- 2026-11-08T03:20Z: stopped: waiting for the client, in design (decision cards 1 and 2)
- 2026-11-08T06:02Z: resumed: in design, from commit `5d0b9e2`
- 2026-11-08T12:48Z: stopped: usage limit, in implement (5-hour window at 80%, resets at 2026-11-08T15:30Z)
- 2026-11-08T15:41Z: resumed: in implement, from commit `4f8d2c0`
- 2026-11-08T16:20Z: stopped: waiting for the maintainer, in implement (design could not answer again: A-2 cannot be built within the conventions)
- 2026-11-08T16:45Z: resumed: in implement, from commit `4f17fcd` (withdraw A-2, by the maintainer's decision: it cannot be built, because opening the database in api/internal/http breaks the conventions' import rule for that package; the architect answers the clock again)
- 2026-11-08T21:40Z: stopped: waiting for the client, in merge (acceptance of delivery-1)
- 2026-11-09T09:05Z: resumed: in merge, from commit `6c1e8f3`
- 2026-11-09T09:12Z: done
