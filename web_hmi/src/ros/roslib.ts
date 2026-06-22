// roslibjs ships a CommonJS source whose entry does `var ROSLIB = this.ROSLIB`
// — top-level `this` is `undefined` once bundled as ESM, which crashes at load.
// The prebuilt browserify UMD has no such issue and attaches ROSLIB to the
// global scope, so we load that and re-export it (fully typed via @types/roslib).
import "roslib/build/roslib.js";

const ROSLIB = (globalThis as unknown as { ROSLIB: typeof import("roslib") }).ROSLIB;

export default ROSLIB;
