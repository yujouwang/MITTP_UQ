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


public class run_uqss_Tall3D_BEPU_runIE extends StarMacro {

  public void execute() {
    change_IC();
    run_ss();
  }


  private void change_IC() {

    Simulation simulation_0 = 
      getActiveSimulation();




    /* Mass flow */
    ScalarGlobalParameter scalarGlobalParameter_0 = 
      ((ScalarGlobalParameter) simulation_0.get(GlobalParameterManager.class).getObject("mflow"));

    Units units_0 = 
      ((Units) simulation_0.getUnitsManager().getObject("kg/s"));

    scalarGlobalParameter_0.getQuantity().setValueAndUnits(MASSFLOW, units_0); // change MASSFLOW

    /* T_in */
    ScalarGlobalParameter scalarGlobalParameter_2 = 
      ((ScalarGlobalParameter) simulation_0.get(GlobalParameterManager.class).getObject("T_in"));

    Units units_1 = 
      ((Units) simulation_0.getUnitsManager().getObject("K"));

    scalarGlobalParameter_2.getQuantity().setValueAndUnits(TIN, units_1); // change TIN



	/*Heat flux*/
    ScalarGlobalParameter scalarGlobalParameter_1 = 
      ((ScalarGlobalParameter) simulation_0.get(GlobalParameterManager.class).getObject("q"));

    Units units_2 = 
      ((Units) simulation_0.getUnitsManager().getObject("W"));

    scalarGlobalParameter_1.getQuantity().setValueAndUnits(POWERIN, units_2);

	
    /* LBE: Continuum  */
    PhysicsContinuum physicsContinuum_0 = 
      ((PhysicsContinuum) simulation_0.getContinuumManager().getContinuum("Physics 1 Fluid"));

    SingleComponentLiquidModel singleComponentLiquidModel_0 = 
      physicsContinuum_0.getModelManager().getModel(SingleComponentLiquidModel.class);

    Liquid liquid_0 = 
      ((Liquid) singleComponentLiquidModel_0.getMaterial());


    /* LBE Density  */
    TemperaturePolynomial temperaturePolynomial_0 = 
      ((TemperaturePolynomial) liquid_0.getMaterialProperties().getMaterialProperty(UserDefinedDensityProperty.class).getMethod());

    Polynomial polynomial_0 = 
      temperaturePolynomial_0.getPolynomial();

    polynomial_0.setCoefficients(new DoubleVector(new double[] {RHO_LBE, -1.22})); // change rho_lbe

    /* LBE Cp  */
    PolynomialSpecificHeat polynomialSpecificHeat_0 = 
      ((PolynomialSpecificHeat) liquid_0.getMaterialProperties().getMaterialProperty(SpecificHeatProperty.class).getMethod());

    Polynomial polynomial_1 = 
      polynomialSpecificHeat_0.getPolynomial();

    polynomial_1.setCoefficients(new DoubleVector(new double[] {Cp_LBE, 0.005934, 7183000.0})); // change Cp_LBE

    /* LBE thermal conductivity  */
    TemperaturePolynomial temperaturePolynomial_1 = 
      ((TemperaturePolynomial) liquid_0.getMaterialProperties().getMaterialProperty(ThermalConductivityProperty.class).getMethod());

    Polynomial polynomial_2 = 
      temperaturePolynomial_1.getPolynomial();

    polynomial_2.setCoefficients(new DoubleVector(new double[] {K_LBE, 0.0095})); // change K_LBE

    /* LBE Dynamic viscosity  */
    UserFieldFunction userFieldFunction_0 = 
      ((UserFieldFunction) simulation_0.getFieldFunctionManager().getFunction("LBE dynamic viscosity")); 

    userFieldFunction_0.setDefinition("MU_LBE * exp(754.1/${Temperature})"); // change MU_LBE

  }

  private void run_ss() {

    Simulation simulation_0 = 
      getActiveSimulation();

    //Clean up solutions
    Solution solution_0 = 
      simulation_0.getSolution();
    solution_0.clearSolution(Solution.Clear.History);

    // Set Stopping Criteria
    StepStoppingCriterion stepStoppingCriterion_0 = 
      ((StepStoppingCriterion) simulation_0.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Steps"));
    IntegerValue integerValue_0 = 
      stepStoppingCriterion_0.getMaximumNumberStepsObject();
    integerValue_0.getQuantity().setValue(SS_ITERATIONS); // change max iter for ss

    // Run
    simulation_0.getSimulationIterator().run();

    // Export the ils
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

    XYPlot xYPlot_3 = 
      ((XYPlot) simulation_0.getPlotManager().getPlot("Temperature"));
    xYPlot_3.export("Temperature.csv", ",");

  }


}
