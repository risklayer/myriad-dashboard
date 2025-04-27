import fs from "fs";

const columns = [
  "eq_A",
  "eq_B",
  "eq_C",
  "eq_D",
  "eq_E",
  "eq_F",
  "eq_G",
  "eq_H",
  "eq_I",
  "eq_J",
  "eq_K",
  "eq_L",
  "eq_M",
  "eq_N",
  "eq_O",
  "eq_P",
  "eq_Q",
  "eq_R",
  "eq_S",
  "flood_A",
  "flood_B",
  "flood_C",
  "flood_D",
  "flood_E",
  "flood_F",
  "flood_G",
  "flood_H",
  "flood_I",
  "flood_J",
  "flood_K",
  "flood_L",
  "flood_M",
  "flood_N",
  "flood_O",
  "flood_P",
  "flood_Q",
  "flood_R",
  "flood_S",
  "total_A",
  "total_B",
  "total_C",
  "total_D",
  "total_E",
  "total_F",
  "total_G",
  "total_H",
  "total_I",
  "total_J",
  "total_K",
  "total_L",
  "total_M",
  "total_N",
  "total_O",
  "total_P",
  "total_Q",
  "total_R",
  "total_S",
].reduce(
  (att, key) => {
    const [h, code] = key.split("_");
    const field_name = `Danube_multi_hazard_scenario_A21_${key}`;
    const hazardMap = {
      flood: {
        hazard: "flood",
        description: `Amount of capital stock in million EUR for NACE Rev 2.1 code ${code} affected by the modelled flood scenario.`,
      },
      eq: {
        hazard: "EQ",
        description: `Amount of capital stock in million EUR for NACE Rev 2.1 code ${code} affected by the modelled earthquake scenario.`,
      },
      total: {
        hazard: "EQ_flood",
        description: `Amount of capital stock in million EUR for NACE Rev 2.1 code ${code} affected by the modelled flood and earthquake scenario.`,
      },
    };

    const meta = {
      field_name,
      nace_code: code,
      ...hazardMap[h],
      // return_period: null,
      // threshold: null,
      exposure: `A21_${code}`,
    };
    return {
      ...att,
      [key]: meta,
      // nace_code: code,
    };
  },
  {
    fp_eq: {
      field_name: "Danube_multi_hazard_scenario_earthquake_footprint",
      hazard: "EQ",
      // exposure: "fp_eq",
      category: "fp_eq",
      description: `Earthquake Intensity (MMI) for the modelled earthquake scenario`,
    },

    fp_fl: {
      field_name: "Danube_multi_hazard_scenario_earthquake_footprint",
      hazard: "flood",
      // exposure: "fp_fl",
      category: "fp_fl",
      description: `Average water depth in flooded areas (metres) for the modelled flood scenario`,
    },
  }
);

const alphabet = "ABCDEFGHIJKLMNOPQRS".split("");
const naceCodeDictionary = alphabet.reduce((acc, a) => ({ ...acc, [a]: a }), {
  // fp_eq: "Earthquake intensity",
  // fp_fl: "Floodwater depth",
});

const final = {
  columns,
  parameters: {
    values: {},
    threshold: { values: {} },
    exposure: { values: {} },
    return_period: { values: {} },
    additonal_metadata: {
      category: {
        label: "Category",
        unit: null,
        values: {
          fp_eq: "Earthquake intensity",
          fp_fl: "Floodwater depth",
        },
      },
      nace_code: {
        label: "NACE Code",
        unit: null,
        values: {
          ...naceCodeDictionary,
        },
      },
    },
  },
  // threshold: {
  //   label: "Threshold",
  //   values: {},
  // },
  exposure: {
    label: "Exposure",
    values: {
      fp_eq: {
        label: "Earthquake footprint",
        unit: "MMI",
      },
      fp_fl: {
        label: "Flood footprint",
        unit: "m",
      },
      A21_ALL: {
        label: "total A21 capital stock in million EUR",
        unit: "million EUR",
      },
      A21_A: {
        label: "capital stock in million EUR for NACE Rev 2.1 code A",
        unit: "million EUR",
      },
      A21_B: {
        label: "capital stock in million EUR for NACE Rev 2.1 code B",
        unit: "million EUR",
      },
      A21_C: {
        label: "capital stock in million EUR for NACE Rev 2.1 code C",
        unit: "million EUR",
      },
      A21_D: {
        label: "capital stock in million EUR for NACE Rev 2.1 code D",
        unit: "million EUR",
      },
      A21_E: {
        label: "capital stock in million EUR for NACE Rev 2.1 code E",
        unit: "million EUR",
      },
      A21_F: {
        label: "capital stock in million EUR for NACE Rev 2.1 code F",
        unit: "million EUR",
      },
      A21_G: {
        label: "capital stock in million EUR for NACE Rev 2.1 code G",
        unit: "million EUR",
      },
      A21_H: {
        label: "capital stock in million EUR for NACE Rev 2.1 code H",
        unit: "million EUR",
      },
      A21_I: {
        label: "capital stock in million EUR for NACE Rev 2.1 code I",
        unit: "million EUR",
      },
      A21_J: {
        label: "capital stock in million EUR for NACE Rev 2.1 code J",
        unit: "million EUR",
      },
      A21_K: {
        label: "capital stock in million EUR for NACE Rev 2.1 code K",
        unit: "million EUR",
      },
      A21_L: {
        label: "capital stock in million EUR for NACE Rev 2.1 code L",
        unit: "million EUR",
      },
      A21_M: {
        label: "capital stock in million EUR for NACE Rev 2.1 code M",
        unit: "million EUR",
      },
      A21_N: {
        label: "capital stock in million EUR for NACE Rev 2.1 code N",
        unit: "million EUR",
      },
      A21_O: {
        label: "capital stock in million EUR for NACE Rev 2.1 code O",
        unit: "million EUR",
      },
      A21_P: {
        label: "capital stock in million EUR for NACE Rev 2.1 code P",
        unit: "million EUR",
      },
      A21_Q: {
        label: "capital stock in million EUR for NACE Rev 2.1 code Q",
        unit: "million EUR",
      },
      A21_R: {
        label: "capital stock in million EUR for NACE Rev 2.1 code R",
        unit: "million EUR",
      },
      A21_S: {
        label: "capital stock in million EUR for NACE Rev 2.1 code S",
        unit: "million EUR",
      },
      A21_T: {
        label: "capital stock in million EUR for NACE Rev 2.1 code T",
        unit: "million EUR",
      },
    },
  },
  hazard: {
    label: "Hazard",
    values: {
      EQ: {
        label: "Earthquake",
        unit: "g",
      },
      flood: {
        label: "Flood",
        unit: "m",
      },
      EQ_flood: {
        label: "Earthquake and Flood",
        unit: null,
      },
    },
  },
};

var json = JSON.stringify(final);
fs.writeFileSync("danube_metadata.json", json);
