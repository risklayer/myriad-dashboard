import L from "leaflet";

const GrayscaleTileLayer = L.TileLayer.extend({
  options: {
    quotaRed: 21,
    quotaGreen: 21,
    quotaBlue: 26,
    quotaDividerTune: 33,
    quotaDivider: function () {
      return (
        this.quotaRed + this.quotaGreen + this.quotaBlue + this.quotaDividerTune
      );
    },
  },

  initialize: function (url: string, options: L.TileLayerOptions) {
    options = options || {};
    options.crossOrigin = true;
    // @ts-expect-error initialize is undocumented
    L.TileLayer.prototype.initialize.call(this, url, options);

    this.on("tileload", function (e) {
      // @ts-expect-error _makeGrayscale is undocumented
      (this as typeof GrayscaleTileLayer)._makeGrayscale(e.tile);
    });
  },

  _createTile: function () {
    // @ts-expect-error _createTile is undocumented
    const tile = L.TileLayer.prototype._createTile.call(this);
    tile.crossOrigin = "Anonymous";
    return tile;
  },

  _makeGrayscale: function (img: HTMLImageElement) {
    if (img.getAttribute("data-grayscaled")) {
      return;
    }

    img.crossOrigin = "";
    const canvas = document.createElement("canvas")!;
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(img, 0, 0);

    const imgd = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pix = imgd.data;
    for (let i = 0, n = pix.length; i < n; i += 4) {
      pix[i] =
        pix[i + 1] =
        pix[i + 2] =
          (this.options.quotaRed * pix[i]! +
            this.options.quotaGreen * pix[i + 1]! +
            this.options.quotaBlue * pix[i + 2]!) /
          this.options.quotaDivider();
    }
    ctx.putImageData(imgd, 0, 0);
    img.setAttribute("data-grayscaled", "");
    img.src = canvas.toDataURL();
  },
}) as unknown as typeof L.TileLayer;
export function grayscaleTileLayer(url: string, options: L.TileLayerOptions) {
  return new GrayscaleTileLayer(url, options);
}
