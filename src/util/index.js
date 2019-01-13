import chalk from 'chalk';
import { sprintf } from 'sprintf-js';
import { rgbToHsv } from 'colorsys';

export const now = () => {
  return Math.round(new Date().getTime() / 1000);
};

export const colourMessage = (hue, msg) => chalk.hsv(hue, 50, 100)(msg);

const colourFormat = '{R:%03d G:%03d B:%03d}';

/**
 * Convert a single colorsys object to string
 * @param {colorsys RGB object} colour
 */
export const colourToString = colour => {
  return sprintf(colourFormat, colour.r, colour.g, colour.b);
};

/**
 * Convert a colours specification to string
 * @param {Array of colorsys RGB objects} colours
 */
export const coloursToString = colours => {
  const prefixFormat = `%0${Math.ceil(Math.log10(colours.length))}d | `;
  return colours.reduce((accumulator, colour, count) => {
    return accumulator.concat(
      colourMessage(
        rgbToHsv(colour).h,
        sprintf(prefixFormat, count) + colourToString(colour) + '\n'
      )
    );
  }, '');
};

export const colourRateLogger = context => {
  const { start, lastPrint = now(), frames, channelColours } = context;
  context.frames += 1;
  if (now() - lastPrint > 1) {
    context.rate = frames / (now() - start + 1);
    const someColour = channelColours[Object.keys(channelColours)[0]][0];
    console.log(
      colourMessage(
        rgbToHsv(someColour).h,
        `${colourToString(someColour)} :  ${context.rate.toFixed(2)}`
      )
    );
    context.lastPrint = now();
  }
  return context;
};

export const consoleErrorHandler = e => {
  if (e) console.error(e);
};
