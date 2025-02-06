let vuln_charts = new Map();
let vuln_datasets = new Map();
function displayCurveChart(panel) {
  const curve_element = document.getElementById(
    `id_curve_values_json-${panel}`
  );
  const curve = curve_element && JSON.parse(curve_element.value);
  if (!curve) {
    vuln_chart?.destroy?.();
    return;
  }

  const id = curve?.key ?? null;
  const row_selector = document.querySelector(`#id_panel_${panel}_row`);
  row_selector.value = id;
  let vuln_chart = vuln_charts.get(panel);
  const vuln_dataset = vuln_datasets.get(panel);
  if (!curve) {
    vuln_chart?.destroy?.();
    return;
  }
  const data = curve.values_xy.map(([x, y]) => ({ x, y }));
  const datasets = [
    {
      data,
      label: curve.x_label,
    },
  ];
  if (
    vuln_chart &&
    vuln_chart.canvas &&
    vuln_dataset &&
    vuln_dataset.x_label === curve.x_label &&
    vuln_dataset.y_label === curve.y_label
  ) {
    vuln_chart.data = {
      datasets,
    };
    vuln_chart.update();
  } else {
    vuln_chart?.destroy?.();
    vuln_chart = new Chart(
      document.getElementById(`vulnerability-curve-chart-${panel}`),
      {
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
              display: false,
            },
          },
          scales: {
            x: {
              title: {
                display: true,
                text: curve.x_label,
              },
            },
            y: {
              title: {
                display: true,
                text: curve.y_label,
              },
            },
          },
        },
      }
    );
  }
  vuln_charts.set(panel, vuln_chart);
  vuln_datasets.set(panel, curve);
}
async function copyToClipboard(selector) {
  const textarea = document.querySelector(selector);
  const text = textarea.value;
  try {
    await navigator.clipboard.writeText(text);
    toast("Data copied to clipboard");
    console.log("Content copied to clipboard");
  } catch (err) {
    console.error("Failed to copy: ", err);
    toast("Data was NOT copied to clipboard");
  }
}
async function downloadFile(selector) {
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
}

function copyFilters(panel) {
  const sourceForm = document.querySelector(
    `#panel-${panel} .curve-filter-form`
  );
  const targetForm = document.querySelector(
    `#panel-${3 - panel} .curve-filter-form`
  );
  for (const input of sourceForm.elements) {
    if (input.tagName === "SELECT") {
      const name = input.name;
      targetForm[name].value = input.value;
    }
    targetForm.dispatchEvent(new Event("change"));
  }
}

function setFiltersFromCurve(panel) {
  const sourceTable = document.querySelector(
    `#panel-${panel} .curve-details-table`
  );
  const targetForm = document.querySelector(
    `#panel-${panel} .curve-filter-form`
  );
  for (const th of sourceTable.querySelectorAll("th")) {
    const name = th.dataset["name"];
    if (name && targetForm[name]) {
      value = th.dataset["value"];
      targetForm[name].value = value;
    }
  }
  targetForm.dispatchEvent(new Event("change"));
}

addEventListener("DOMContentLoaded", (event) => {
  // When opening/closing one set of filters, do the same for the other one
  const detailsFields = document.querySelectorAll(".curve-filter-details");
  detailsFields.forEach((details) =>
    details.addEventListener("toggle", (event) => {
      detailsFields.forEach((dets) => {
        if (dets !== details) {
          dets.toggleAttribute("open", details.open);
        }
      });
    })
  );
});
