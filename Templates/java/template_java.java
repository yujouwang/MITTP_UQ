// Simcenter STAR-CCM+ macro: elbow_input.java
// Written by Simcenter STAR-CCM+ 19.04.009
package macro;

import java.util.*;

import star.common.*;
import star.base.neo.*;
import star.turbulence.*;




public class template_java extends StarMacro {

  public void execute() {
    change_IC();
    turn_on_viscosity_perturbation();
    run();
  }

  private void change_IC() {

    Simulation simulation_0 = 
      getActiveSimulation();

    /* ==================================================
        Customize: perturb through field functions 
     =================================================*/
    // UserFieldFunction userFieldFunction_0 = 
    // ((UserFieldFunction) simulation_0.getFieldFunctionManager().getFunction("0_perturbed_mass_flow"));
    // userFieldFunction_0.setDefinition("${IHT Mass Flow} * VAR_1");

    // Add more if needed...

  }
  
  private void turn_on_viscosity_perturbation() {

    Simulation simulation_0 = 
      getActiveSimulation();

    // Turn on the user eddy viscosity scaling
    Region region_0 = 
      simulation_0.getRegionManager().getRegion("My region name"); // Change to your region name

    TurbulentViscosityUserScalingProfile turbulentViscosityUserScalingProfile_0 = 
      region_0.getValues().get(TurbulentViscosityUserScalingProfile.class);

    //Set the user scaling method as xyz table 
    turbulentViscosityUserScalingProfile_0.setMethod(XyzTabularScalarProfileMethod.class);

    // Set table "rf.csv"
    FileTable fileTable_1 = 
      ((FileTable) simulation_0.getTableManager().getTable("rf"));
    turbulentViscosityUserScalingProfile_0.getMethod(XyzTabularScalarProfileMethod.class).setTable(fileTable_1);
    // Use the value "phi"
    turbulentViscosityUserScalingProfile_0.getMethod(XyzTabularScalarProfileMethod.class).setData("phi");
    
    // Reload the rf.csv
    FileTable fileTable_0 = 
      ((FileTable) simulation_0.getTableManager().getTable("rf"));
    fileTable_0.extract();
  }
  
  private void run() {

    Simulation simulation_0 = 
      getActiveSimulation();
      
    // Set Stopping Criteria
    StepStoppingCriterion stepStoppingCriterion_0 = 
      ((StepStoppingCriterion) simulation_0.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Steps"));

    IntegerValue integerValue_0 = 
      stepStoppingCriterion_0.getMaximumNumberStepsObject();

    integerValue_0.getQuantity().setValue(5);


   // Clean solution history
    Solution solution_0 = 
      simulation_0.getSolution();

    solution_0.clearSolution(Solution.Clear.History);

    // Run
    simulation_0.getSimulationIterator().run();

  }
  
}