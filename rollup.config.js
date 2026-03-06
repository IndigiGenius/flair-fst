import { nodeResolve } from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
import image from '@rollup/plugin-image';
import terser from '@rollup/plugin-terser';

export default {
  input: 'js/flair-fst.ts',
  output: {
    dir: 'src/flair_fst/assets',
    format: 'esm'
  },
  plugins: [image(), typescript(), terser(), nodeResolve()]
};
