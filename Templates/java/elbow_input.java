// Simcenter STAR-CCM+ macro: elbow_input.java
// Written by Simcenter STAR-CCM+ 19.04.009
package macro;

import java.util.*;

import star.common.*;
import star.base.neo.*;

public class elbow_input extends StarMacro {

  public void execute() {
    execute0();
  }

  private void execute0() {

    Simulation simulation_0 = 
      getActiveSimulation();

    UserFieldFunction userFieldFunction_0 = 
      ((UserFieldFunction) simulation_0.getFieldFunctionManager().getFunction("0_perturbed_mass_flow"));

    userFieldFunction_0.setDefinition("${IHT Mass Flow} * IHT_MASSFLOW");
  }
}
