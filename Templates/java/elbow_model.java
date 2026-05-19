// Simcenter STAR-CCM+ macro: elbow_model.java
// Written by Simcenter STAR-CCM+ 19.04.009
package macro;

import java.util.*;

import star.common.*;
import star.base.neo.*;
import star.turbulence.*;

public class elbow_model extends StarMacro {

  public void execute() {
    turn_on_viscosity_perturbation();
  }

  private void turn_on_viscosity_perturbation() {

    Simulation simulation_0 = 
      getActiveSimulation();

    Region region_0 = 
      simulation_0.getRegionManager().getRegion("IHT Hot Leg Pipe");

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
  }
}
