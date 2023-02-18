# Mars 2020 Entry-Descent-Landing Case Study

This case study illustrates different approaches for encoding the Mars 2020 EDL phase timeline as algebraic contracts using Pacti.

## [Initial encoding](mars_edl-1st-encoding.ipynb)

The 1st encoding attempt reflects the similarity between a phase segment and a corresponding contract for that segment:
- The entry conditions of the segment correspond to the assumptions of the corresponding contract.
- The exit conditions of the segment correspond to the guarantees of the corresponding contract.

an approach that ought to be sensible and intuitive to an audience unfamiliar with thinking about scenarios from the perspective of segmenting them into what the EDL engineers call segments characterized using entry and exit conditions. This approach, albeit unsuccessful, helps convey the relationship between entry/exit conditions and assume/guarantee constraints in an algebraic contract setting.

## [An improved encoding](mars_edl-2nd-encoding.ipynb)

