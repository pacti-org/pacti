# Case Studies
In the following sections we will present case studies that illustrate the use of pacti for different applications.

<font size="5">[**Safety of autonomous vehicles**](/pacti/_case_studies/evaluating_perception/saved_results/)</font>

We present a case study to evaluate the perception system of an autonomous car using the _quotient_ operator.

<img src="/pacti/_case_studies/evaluating_perception/imglib/autonomy-stack.png" alt= "autonomy figure" width="700"/>

<font size="5">[**Trajectory planning for multi-agent systems**](/pacti/_case_studies/multiagent_coordination/multiagent/)</font>

A case study on multi-agent path finding (MAPF) where multiple agents need to reach their target location on a grid world according to a conflict-free strategy.
We treat each time step as our viewpoint to find a solution that satisfies the agents' dynamics and collision constraints using the _merge_ operator.

<img src="https://github.com/FormalSystems/media/blob/main/case_studies/multiagent_coordination/multiagent_overview.png?raw=true" alt= "multiagent figure" width="700"/>

<font size="5">[**Specification-based synthetic biology**](/pacti/_case_studies/biocircuit_specifications/specification_based_synthetic_biology/)</font>

A case study on modeling the specifications of a biological circuit and speed up the experimental design process by finding optimal components to use from a library of parts. In the case study, we first build a characterized library of parts as assume-guarantee contracts using existing experimental data from the literature.With the use of _Pacti_, we demonstrate how scientists may describe the desired top-level behavior as contracts and then computationally choose from a library of available parts to ensure that the components meet the top-level system specification. For the engineered bacteria case study, we find the specification of the sensors that meet the top-level criteria on fold-change of the circuit response. Finally, we also show how we can find the specifications of missing parts in a system. In synthetic biology, it is common to have parts in the system for which no characterization data is available. Using quotient operation on contracts, we can find the constraints that this missing part must satisfy to meet the desired top-level criteria.

<font size="5">[**Signal processing pipelines in digital ICs**](/pacti/_case_studies/digital_signal_processing/dsp_wl/)</font>

A case study on word length analysis and optimization for digital signal processing circuit design.
<img src="https://github.com/FormalSystems/media/blob/main/case_studies/digital_signal_processing/digital_filter_flow.png?raw=True" alt= "DSP figure" width="700"/>


<font size="5">[**Generating UAV topologies**](/pacti/_case_studies/uav_topologies/topologies/)</font>

<img src="https://raw.githubusercontent.com/FormalSystems/media/main/case_studies/uav_topologies/grammar-1.png" alt= "uav topologies" width="700"/>

We demonstrate the application of pacti in modeling a context-sensitive grammar for generating three-dimensional topologies for Unmanned Aerial Vehicles (UAVs).

# Space Mission

A case study on modeling the specifications of autonomous tasks for a planning/scheduling onboard of a space mission system.
