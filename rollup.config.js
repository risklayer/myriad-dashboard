import fs from "fs";
import commonjs from "@rollup/plugin-commonjs";
import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";
import { createRollupLicensePlugin } from "rollup-license-plugin";
import _ from "lodash";

const isProduction = process.env.NODE_ENV === "production";

const inputFiles = [
  "dashboard/js/scripts.ts",
  "curve_explorer/js/curve_explorer.ts",
  "exposure_at_risk/js/exposure_at_risk.ts",
  "scenario_calculator/js/scenario_calculator.ts",
  "showcase/js/showcase.ts",
];

export default {
  input: inputFiles,
  output: {
    dir: "build/js",
    // format: "umd",
    sourcemap: true,
  },
  plugins: [
    {
      name: "ejs",
      async transform(src, id) {
        if (id.endsWith(".ejs")) {
          const code = _.template(src, {
            variable: "data",
            sourceURL: id,
          }).source;
          return `import { escape } from "lodash";\nconst _ = { escape };\nexport default ${code}`;
        }
      },
    },
    commonjs(),
    resolve(),
    typescript({
      exclude: ["**/static/**", "build/**"],
      compilerOptions: {
        lib: ["es6", "dom"],
        target: "es6",
      },
      sourceMap: !isProduction,
    }),
    isProduction && (await import("@rollup/plugin-terser")).default(),
    createRollupLicensePlugin({
      exclude: "*.ejs",
      includePackages() {
        // These packages are included as script tags so need manual inclusion
        return [
          "node_modules/@popperjs/core",
          "node_modules/bootstrap",
          "node_modules/georaster",
          "node_modules/htmx.org",
          "node_modules/jszip",
          // "node_modules/htmx-ext-class-tools", // No license listed
        ];
      },
      // licenseOverrides: {
      // },
      additionalFiles: {
        "oss-licenses.html": async (items) => {
          const pythonLicensesFile = fs.readFileSync(
            "./dashboard/py-oss-licenses.json"
          );
          const pythonLicenses = JSON.parse(pythonLicensesFile).map((item) =>
            _.mapKeys(item, (value, key) => _.camelCase(key))
          );
          const licensesTemplate = _.template(
            fs.readFileSync("./licensesTemplate.ejs", "utf-8"),
            {
              variable: "data",
              client: false,
              strict: true,
              sourceURL: "licensesTemplate.ejs",
            }
          );
          return licensesTemplate({
            items: _.sortBy([...items, ...pythonLicenses], "name"),
          });
        },
      },
    }),
  ],
  onwarn(warning, warn) {
    if (warning.code === "THIS_IS_UNDEFINED") return;
    warn(warning);
  },
};
