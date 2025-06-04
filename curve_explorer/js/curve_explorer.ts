import {
  CategoryScale,
  Chart,
  LinearScale,
  ScatterController,
  PointElement,
  LineElement,
} from "chart.js";

declare global {
  interface Window {
    displayCurveChart: (panel: number, force: boolean) => void;
    copyFilters: (panel: number) => void;
    copyToClipboard: (selector: string) => void;
    setFilters: (panel: number) => Promise<void>;
    downloadFile: (selector: string) => Promise<void>;
  }
}

Chart.register(
  CategoryScale,
  LinearScale,
  ScatterController,
  PointElement,
  LineElement
);

const vuln_charts = new Map();
const vuln_datasets = new Map();

window.displayCurveChart = function displayCurveChart(
  panel: number,
  force: boolean
) {
  const curves = [0, 1].map(getCurveObject);
  const [curve1, curve2] = curves;
  const [chart1, chart2, combined_chart] = [0, 1, 2].map((i) =>
    vuln_charts.get(i)
  );

  [curve1, curve2].forEach((curve, i) => {
    const id = curve?.key ?? null;
    if (!id) {
      return;
    }
    const row_selector = document.querySelector(
      `#id_panel_${i}_row`
    ) as HTMLInputElement;
    // Ensure that dropdown gets updated to match when filtering or showing
    // a pinned curve (seems to be a htmx bug)
    if (row_selector) {
      row_selector.value = id;
    }
  });

  if (!curve1) {
    chart1?.destroy?.();
  }
  if (!curve2) {
    chart2?.destroy?.();
  }

  const show_combined =
    curve1 &&
    curve2 &&
    curve1.hazard === curve2.hazard &&
    curve1.IM_units === curve2.IM_units &&
    curve1.Y_Description === curve2.Y_Description;

  if (!show_combined) {
    combined_chart?.destroy?.();
    document
      .getElementById("combined-curve-chart-card")!
      .classList.add("d-none");
  }

  if (!curves[panel]) {
    return;
  }

  // Draw single-curve chart (might be hidden behind the other, but only drawn once)
  drawChart(panel, force, curves[panel]);

  if (show_combined) {
    // Populate the combined chart
    document
      .getElementById("combined-curve-chart-card")!
      .classList.remove("d-none");
    drawChart(2, force, curve1, curve2.key !== curve1.key ? curve2 : null);
  }
};

function drawChart(
  panel: number,
  force: boolean,
  ...curves: Record<string, unknown>[]
) {
  if (!curves.length) {
    return;
  }

  const styles = window.getComputedStyle(document.body);
  const body = styles.getPropertyValue("--bs-body-color");
  const border = styles.getPropertyValue("--bs-border-color");
  const color1 = styles.getPropertyValue("--bs-blue");
  const color2 = styles.getPropertyValue("--bs-purple");
  const colors = [color1, color2];

  const datasets = curves.filter(Boolean).map((curve, i) => {
    const data = (curve.values_xy as [number, number][]).map(([x, y]) => ({
      x,
      y,
    }));
    return {
      data,
      color: colors[i]!,
      borderColor: colors[i]!,
      backgroundColor: colors[i]!,
      label: curve.label as string,
    };
  });

  const canvas = document.getElementById(
    `vulnerability-curve-chart-${panel}`
  ) as HTMLCanvasElement;
  const vuln_dataset = vuln_datasets.get(panel);
  let vuln_chart = vuln_charts.get(panel);
  if (
    !force &&
    vuln_chart &&
    vuln_chart.canvas &&
    vuln_dataset &&
    vuln_dataset.IM_units === curves[0]!.IM_units &&
    vuln_dataset.Y_Description === curves[0]!.Y_Description
  ) {
    // If the chart already exists and has equivalent axes, just update it
    vuln_chart.data = {
      datasets,
    };
    vuln_chart.update();
  } else {
    // Otherwise remove it and start from scratch
    vuln_chart?.destroy?.();
    // Text color
    Chart.defaults.color = body;
    vuln_chart = new Chart(canvas, {
      type: "scatter",
      data: {
        datasets,
      },
      options: {
        showLine: true,
        cubicInterpolationMode: "monotone",
        animations: [],
        plugins: {
          legend: {
            display: curves.length > 1,
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: `Intensity Measure (${curves[0]!.IM_units})`,
            },
            grid: {
              color: border,
            },
          },
          y: {
            title: {
              display: true,
              text: (curves[0]!.Y_Description as string) || "Damage Ratio",
            },
            grid: {
              color: border,
            },
          },
        },
      },
    });
  }

  // Save for comparison on the next draw
  vuln_charts.set(panel, vuln_chart);
  vuln_datasets.set(panel, curves[0]);
}

// Extract the JSON of the curve from the textarea
function getCurveObject(panel: number) {
  const curve_element = document.getElementById(
    `id_curve_values_json-${panel}`
  ) as HTMLTextAreaElement;
  const curve = curve_element && JSON.parse(curve_element.value);
  return curve;
}

window.copyToClipboard = async function copyToClipboard(selector: string) {
  const textarea = document.querySelector(selector) as HTMLTextAreaElement;
  const text = textarea.value;
  try {
    await navigator.clipboard.writeText(text);
    toast("Data copied to clipboard");
    console.log("Content copied to clipboard");
  } catch (err) {
    console.error("Failed to copy: ", err);
    toast("Data was NOT copied to clipboard");
  }
};

window.downloadFile = async function downloadFile(selector: string) {
  const textarea = document.querySelector(selector);
  const text = textarea.value;
  try {
    const format = textarea.dataset.format;
    const filename = textarea.dataset.filename;
    const blob = new Blob([text], { type: `text/${format}` });
    const anchor = document.createElement("a");

    anchor.download = filename;
    anchor.href = (window.webkitURL || window.URL).createObjectURL(blob);
    anchor.dataset.downloadurl = [
      `text/${format}`,
      anchor.download,
      anchor.href,
    ].join(":");
    anchor.click();
  } catch (err) {
    console.error("Failed to download: ", err);
    toast("Error creating download");
  }
};

window.copyFilters = function copyFilters(panel: number) {
  const sourceForm = document.querySelector(
    `#panel-${panel} .curve-filter-form`
  ) as HTMLFormElement;
  const targetForm = document.querySelector(
    `#panel-${1 - panel} .curve-filter-form`
  ) as HTMLFormElement;
  for (const input of sourceForm.elements) {
    if (input.tagName === "SELECT") {
      const name = input.name;
      (targetForm[name] as HTMLSelectElement).value = input.value;
    }
    targetForm.dispatchEvent(new Event("change"));
  }
};

window.setFilters = function setFilters(panel: number) {
  const sourceTable = document.querySelector(
    `#panel-${panel} .curve-details-table`
  ) as HTMLTableElement;
  const targetForm = document.querySelector(
    `#panel-${panel} .curve-filter-form`
  ) as HTMLFormElement;
  for (const th of sourceTable.querySelectorAll("th")) {
    const name = th.dataset["name"];
    if (name && targetForm[name]) {
      const value = th.dataset["value"];
      (targetForm[name] as HTMLInputElement).value = value;
    }
  }
  targetForm.dispatchEvent(new Event("change"));
};

addEventListener("DOMContentLoaded", () => {
  // When opening/closing one set of filters, do the same for the other one
  const pairedTogglers = ["curve-filter-details", "curve-values-details"];
  window.addEventListener(
    "toggle",
    (event) => {
      const el = event.target as HTMLDetailsElement;
      pairedTogglers.forEach((klass) => {
        if (el.classList.contains(klass)) {
          for (const el2 of document.querySelectorAll(`.${klass}`)) {
            if (el2 !== el) {
              el2.toggleAttribute("open", el.open);
            }
          }
        }
      });
    },
    { capture: true }
  );

  const config = { attributes: true, childList: false, subtree: false };
  const observer = new MutationObserver((mutationList) => {
    for (const mutation of mutationList) {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "data-bs-theme"
      ) {
        console.log(
          `Theme changed to ${(mutation.target as HTMLSelectElement).dataset.bsTheme}.`
        );
        window.displayCurveChart(0, true);
        window.displayCurveChart(1, true);
      }
    }
  });
  observer.observe(document.documentElement, config);
});
