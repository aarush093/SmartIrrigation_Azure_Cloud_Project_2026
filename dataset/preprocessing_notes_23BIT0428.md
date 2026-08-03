# Dataset Preprocessing Notes

Owner: Krishna Agrawal (23BIT0428)

## Scope

Supplementary notes to the dataset specification. This file records the preprocessing decisions taken for the six selected datasets along with the metadata still outstanding at the end of Phase-I.

## Common preprocessing steps

1. Temporal alignment. Weather records arrive at hourly, three hourly and daily resolutions depending on source. All series are resampled to a common daily step before joining, using sums for rainfall and means for temperature and humidity.
2. Unit normalisation. Temperature is standardised to degrees Celsius, rainfall to millimetres and wind speed to metres per second.
3. Missing value handling. Gaps shorter than three days are filled by linear interpolation. Longer gaps are left as null and the affected windows are excluded from training rather than imputed, since imputing a week of rainfall would fabricate the single most important signal.
4. Outlier screening. Physically impossible values such as negative rainfall or humidity above one hundred percent are dropped rather than clipped.
5. Feature derivation. Reference evapotranspiration and rolling rainfall totals over three, seven and fourteen days are computed after cleaning.

## Split strategy

Splits are made by season rather than randomly. A random split leaks information across adjacent days and inflates accuracy.

## Outstanding items for Phase-II

The Kaggle sourced dataset entry still has four fields blank in the specification: URL, size, record count and licence. These were left blank rather than estimated. To be completed before the Phase-II review.
