graph [
  node [
    id 0
    label "Nuclear Medicine"
    type "Medical Field"
    description "Uses small amounts of radioactive material to diagnose or treat disease."
    sources "_networkx_list_start"
    sources "fallback"
  ]
  node [
    id 1
    label "Theranostics"
    type "Medical Approach"
    description "A personalized approach combining diagnostics to identify targets and therapeutics to treat them."
    sources "_networkx_list_start"
    sources "fallback"
  ]
  node [
    id 2
    label "Dosimetry"
    type "Measurement"
    description "The calculation and assessment of the radiation dose absorbed by the patient's body and tumors."
    sources "_networkx_list_start"
    sources "fallback"
  ]
  node [
    id 3
    label "Radioisotope"
    type "Substance"
    description "A radioactive form of an element used for imaging or treatment."
    sources "_networkx_list_start"
    sources "fallback"
  ]
  node [
    id 4
    label "PRRT"
    type "Therapy"
    description "Peptide Receptor Radionuclide Therapy, a type of targeted radioligand therapy."
    sources "_networkx_list_start"
    sources "fallback"
  ]
  node [
    id 5
    label "Lutetium-177"
    type "Radioisotope"
    description "A beta-emitting isotope commonly used in therapeutic nuclear medicine."
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 0
    target 1
    relation "is a modern approach within"
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 0
    target 2
    relation "ensures safe and effective treatment in"
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 1
    target 3
    relation "uses specifically targeted"
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 1
    target 4
    relation "is a prime example of"
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 2
    target 3
    relation "measures the absorbed dose from"
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 2
    target 4
    relation "helps personalize the treatment cycles for"
    sources "_networkx_list_start"
    sources "fallback"
  ]
  edge [
    source 4
    target 5
    relation "is the radiation source for"
    sources "_networkx_list_start"
    sources "fallback"
  ]
]
