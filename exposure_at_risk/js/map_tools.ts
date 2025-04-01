import L from "leaflet";

/**
 * Background option is stored in URL state.
 * Leaflet allows modifying the base layer using an inbuilt Control but not with
 * external API, so instead we'll do it manually by setting the appropriate
 * radio input and letting leaflet do the rest.
 */
export function updateBaseLayer(
  settingsForm: HTMLFormElement,
  baseLayerControl: L.Control
) {
  const baseLayer = settingsForm.base_layer.value;

  if (!baseLayer) {
    return;
  }
  // @ts-ignore
  const { _layerControlInputs: inputs } = baseLayerControl;
  for (const radio of inputs as HTMLInputElement[]) {
    const span = radio.nextElementSibling as HTMLSpanElement;
    // The label span has leading space
    if (span.innerText.trim() === baseLayer) {
      if (!radio.checked) {
        radio.checked = true;
        // Force leaflet to apply the new background
        radio.dispatchEvent(new Event("click"));
      }
      break;
    }
  }
}
