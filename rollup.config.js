import commonjs from "@rollup/plugin-commonjs";
import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

const isProduction = process.env.NODE_ENV === "production";

const inputFiles = [
  "dashboard/js/scripts.ts",
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
  ],
  onwarn(warning, warn) {
    if (warning.code === "THIS_IS_UNDEFINED") return;
    warn(warning);
  },
};
