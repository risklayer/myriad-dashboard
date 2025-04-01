import { round } from "lodash";

export function floatTo3Digits(value: number): string {
  // if (value > 1000000) {
  //   const digits = Math.floor((String(Math.round(value)).length - 4) / 3);
  //   return String(round(value, -digits * 3));
  // }
  if (value > 100) {
    return String(round(value, 0));
  }
  if (value > 10) {
    return String(round(value, 1));
  }
  if (value > 1) {
    return String(round(value, 2));
  }
  if (value > 0.1) {
    return String(round(value, 3));
  }
  if (value > 0.01) {
    return String(round(value, 4));
  }
  if (value > 0.001) {
    return String(round(value, 5));
  }
  if (value > 0.0001) {
    return String(round(value, 6));
  }

  if (value === 0) {
    return "0";
  }

  return value.toExponential(2);
}
