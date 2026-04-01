// Simcenter STAR-CCM+ macro: run_uq.java
// Written by Simcenter STAR-CCM+ 18.02.008
package macro;

import java.util.*;

import star.common.*;
import star.base.neo.*;
import star.turbulence.*;
import star.vis.*;
import star.automation.*;
import star.userdefinedeos.*;
import star.material.*;
import star.energy.*;


public class run_uqss_Tall3D_GRF extends StarMacro {

  public void execute() {
    run_grf();
  }

  private void run_grf() {

    Simulation simulation_0 = 
      getActiveSimulation();

    // Reload RF
    FileTable fileTable_0 = 
      ((FileTable) simulation_0.getTableManager().getTable("rf"));
    fileTable_0.extract();

    // Turn On multiplier
    Region region_0 = 
      simulation_0.getRegionManager().getRegion("fluid");
    TurbulentViscosityUserScalingProfile turbulentViscosityUserScalingProfile_0 = 
      region_0.getValues().get(TurbulentViscosityUserScalingProfile.class);
    UserFieldFunction userFieldFunction_0 = 
      ((UserFieldFunction) simulation_0.getFieldFunctionManager().getFunction("rf-multiplier-wall"));
    turbulentViscosityUserScalingProfile_0.getMethod(FunctionScalarProfileMethod.class).setFieldFunction(userFieldFunction_0);


    //Clean up solutions
    Solution solution_0 = 
      simulation_0.getSolution();
    solution_0.clearSolution(Solution.Clear.History);


    // Set Stopping Criteria
    StepStoppingCriterion stepStoppingCriterion_0 = 
      ((StepStoppingCriterion) simulation_0.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Steps"));
    IntegerValue integerValue_0 = 
      stepStoppingCriterion_0.getMaximumNumberStepsObject();
    integerValue_0.getQuantity().setValue(MAX_ITERATIONS);


    // Run
    simulation_0.getSimulationIterator().run();


    XyzInternalTable xyzInternalTable_0 = 
      ((XyzInternalTable) simulation_0.getTableManager().getTable("ils"));
    xyzInternalTable_0.extract();
    xyzInternalTable_0.export("ils.csv", ",");


    // Export the results
    XYPlot xYPlot_0 = 
      ((XYPlot) simulation_0.getPlotManager().getPlot("TC_horizontal"));
    xYPlot_0.export("TC_horizontal.csv", ",");

    XYPlot xYPlot_1 = 
      ((XYPlot) simulation_0.getPlotManager().getPlot("TC_vertical"));
    xYPlot_1.export("TC_vertical.csv", ",");

    XYPlot xYPlot_2 = 
      ((XYPlot) simulation_0.getPlotManager().getPlot("Jet spread"));
    xYPlot_2.export("Jet_U.csv", ",");

    XYPlot xYPlot_3 = 
      ((XYPlot) simulation_0.getPlotManager().getPlot("Temperature"));
    xYPlot_3.export("Temperature.csv", ",");
  }
}
