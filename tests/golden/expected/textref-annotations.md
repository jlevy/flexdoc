# TextRef annotations

Document: "design.md"
Annotations: 5

## Lines 2-6

    ... earlier lines omitted ...
    2 | 
    3 | First target.
    4 | 
    5 | Second target.
    6 | 
    ... later lines omitted ...

Annotations:
- ID: "a-first"
  Motivations: ["commenting"]
  Target: span
  URI: textref:0.1?doc=design.md&hash=sha256%3A4b35cec681e761310afc82c729c814b15743e01165eeca4a760455615eb79693&type=span&exact=First%20target.&prefix=%23%20Alpha%0A%0A&suffix=%0A%0ASecond%20target.%0A%0A%23%20Omeg&start=9
  Resolution: resolved via source_position
  Source validation: matched
  Range: L3:C1-L3:C14 [9:22)
  Quote: "First target."
  Body: "First note."
- ID: "a-second"
  Motivations: ["bookmarking"]
  Target: point
  URI: textref:0.1?doc=design.md&hash=sha256%3A4b35cec681e761310afc82c729c814b15743e01165eeca4a760455615eb79693&type=point&prefix=%23%20Alpha%0A%0AFirst%20target.%0A%0A&suffix=Second%20target.%0A%0A%23%20Omega%0A&position=24&affinity=after
  Resolution: resolved via source_position
  Source validation: matched
  Range: L5:C1-L5:C1 [24:24)
  Point affinity: after
  Body: "Insertion point."

## Missing
- ID: "missing"
  Motivations: ["commenting"]
  Target: span
  URI: textref:0.1?doc=design.md&type=span&exact=absent
  Resolution: missing
  Source validation: absent

## Ambiguous
- ID: "ambiguous"
  Motivations: ["classifying"]
  Target: span
  URI: textref:0.1?doc=design.md&type=span&exact=target
  Resolution: ambiguous
  Source validation: absent
  Candidates: [15:21), [31:37)

## Orphaned
- ID: "orphan"
  Motivations: ["commenting"]
  Target: span
  URI: textref:0.1?doc=other.md&hash=sha256%3A4b35cec681e761310afc82c729c814b15743e01165eeca4a760455615eb79693&type=span&exact=%23%20Alpha&suffix=%0A%0AFirst%20target.%0A%0ASecond%20&start=0
  Resolution: unsupported
  Source validation: matched
