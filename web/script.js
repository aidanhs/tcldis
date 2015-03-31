(function () {
'use strict';
var miniwidth = 80;
var padwidth = 50;
var linemult = 1.25;
var fontsize = 12 * linemult;

var larrow = 37;
var uarrow = 38;
var rarrow = 39;
var darrow = 40;

// These must be user-supplied
var fillinFn = function () {
    alert('Must define getInitialCode and getDecompileSteps globally');
};
window.getInitialCode = window.getInitialCode || fillinFn;
window.getDecompileSteps = window.getDecompileSteps || fillinFn;

var ActionArea = React.createClass({
    getInitialState: function () {
        window.getInitialCode(function (err, data) {
            this.setState({'code': data});
            setTimeout(this.onDecompileClick, 0);
        }.bind(this));
        return {'code': ''};
    },
    handleChange: function (e) {
        this.setState({'code': e.target.value});
    },
    onDecompileClick: function () {
        this.props.decompileCB(this.state.code);
    },
    render: function () {
        var kdFire = function (keycode) {
           return function () {
               // TODO: what's the right way to create a keydown event?
               var e = new Event('keydown');
               e.keyCode = keycode;
               document.dispatchEvent(e);
           };
        };
        return (
            <div id='actionarea'>
                <div>
                    <div id='directionbuttons'>
                        <button onClick={kdFire(larrow)} style={{'width': '35%', 'left': '0', 'top': '0', 'bottom': '0'}}>&lt;</button>
                        <button onClick={kdFire(uarrow)} style={{'width': '30%', 'left': '35%', 'right': '35%', 'height': '50%', 'top': '0'}}>^</button>
                        <button onClick={kdFire(darrow)} style={{'width': '30%', 'left': '35%', 'right': '35%', 'height': '50%', 'bottom': '0'}}>v</button>
                        <button onClick={kdFire(rarrow)} style={{'width': '35%', 'right': '0', 'top': '0', 'bottom': '0'}}>&gt;</button>
                    </div>
                    <div style={{'textAlign': 'center'}}>(you can also use the arrow keys)</div>
                    <button id='decompilebutton' onClick={this.onDecompileClick}>Decompile!</button>
                </div>
                <div>
                    <textarea onChange={this.handleChange} value={this.state.code} />
                </div>
            </div>
        );
    }
});

var StepPadding = React.createClass({
    shouldComponentUpdate: function (nextProps, nextState) {
        return (
            this.props.stepIdx !== nextProps.stepIdx ||
            this.props.steps !== nextProps.steps ||
            this.props.changes !== nextProps.changes ||
            this.props.offsets[0] !== nextProps.offsets[0] ||
            this.props.offsets[1] !== nextProps.offsets[1]
        );
    },
    render: function () {
        function linefromchange(change, steps, offsets) {
            var numlines, bbi, ii, step,
                c = change,
                cs = c.step, // What step is this change transforming?
                cb = c.bblock, // What block is this change transforming?
                ss = steps;

            numlines = 0;
            bbi = 0; // Which bblock are we looking at right now
            ii = 0; // Which 'line' in the bblock are we looking at right now
            step = ss[cs];
            var starty1, starty2;
            // Find the offset of source lines
            while (true) {
                if (bbi === cb && ii === c.from[0]) {
                    starty1 = numlines;
                }
                if (bbi === cb && ii === c.from[1]) {
                    starty2 = numlines;
                    break;
                }
                if (ii < step[bbi].length) {
                    numlines += step[bbi][ii].split('\n').length;
                    ii++;
                }
                else if (bbi < step.length - 1) { bbi++; ii = 0; }
                else { throw Error(); }
            }

            numlines = 0;
            bbi = 0;
            ii = 0;
            step = ss[cs+1];
            var endy1, endy2;
            // Find the offset of the target lines
            while (true) {
                if (bbi === cb && ii === c.to[0]) {
                    endy1 = numlines;
                }
                if (bbi === cb && ii === c.to[1]) {
                    endy2 = numlines;
                    break;
                }
                if (ii < step[bbi].length) {
                    numlines += step[bbi][ii].split('\n').length;
                    ii++;
                }
                else if (bbi < step.length - 1) { bbi++; ii = 0; }
                else { throw Error(); }
            }

            starty1 = (starty1 * fontsize) - offsets[0];
            starty2 = (starty2 * fontsize) - offsets[0];
            endy1 = (endy1 * fontsize) - offsets[1];
            endy2 = (endy2 * fontsize) - offsets[1];
            var p = padwidth;
            return [
                <line key={1} x1={2*p} y1={starty1} x2={3*p} y2={endy1}/>,
                <line key={2} x1={2*p} y1={starty2} x2={3*p} y2={endy2}/>,

                <line key={3} x1={0} y1={starty1} x2={2*p} y2={starty1} className='guideLine'/>,
                <line key={4} x1={0} y1={starty2} x2={2*p} y2={starty2} className='guideLine'/>,
                <line key={5} x1={3*p} y1={endy1} x2={5*p} y2={endy1}   className='guideLine'/>,
                <line key={6} x1={3*p} y1={endy2} x2={5*p} y2={endy2}   className='guideLine'/>
            ];
        }

        var stepIdx = this.props.stepIdx;
        var lines = [];
        var changes = this.props.changes.map(function (c) {
            if (c.step !== stepIdx) {
                return;
            }
            var shape = (
                <g key={lines.length}>
                    {linefromchange(c, this.props.steps, this.props.offsets)}
                </g>
            );
            lines.push(shape);
        }, this);
        return <div className="step-padding"><div><svg>{lines}</svg></div></div>;
    }
});

var DecompileStepCode = React.createClass({
    shouldComponentUpdate: function (nextProps, nextState) {
        return this.props.step !== nextProps.step;
    },
    render: function () {
        var step = this.props.step;
        return (
            <pre>{step.map(function (bb, bbi) {
                return bb.join('\n');
            }).join('\n')}</pre>
        );
    }
});

var DecompileSteps = React.createClass({
    handleKeyDown: function (e) {
        var key = e.keyCode || e.charCode;
        var stepIdx = this.state.stepIdx;
        if (key === larrow) { this.changeStepIdx(-1); }
        else if (key === rarrow) { this.changeStepIdx(1); }
        else if (key === uarrow) { this.showMiniSteps(true); }
        else if (key === darrow) { this.showMiniSteps(false); }
        else { return true; }
        e.preventDefault();
        return false;
    },
    showMiniSteps: function (shouldShow) {
        this.setState({'miniStepsOnly': shouldShow});
    },
    changeStepIdx: function (idxChange) {
        var stepIdx = this.state.stepIdx + idxChange;
        if (!(stepIdx < 0 || stepIdx >= this.props.steps.length)) {
            this.setState({'stepIdx': stepIdx});
        }
        // Lazy way of updating the offsets - since react re-uses the
        // DOM nodes, scrolled elements will be in the same place.
        this.handleScroll();
    },
    componentDidMount: function () {
        document.addEventListener('keydown', (function (e) {
            // If it's not fired on the textarea, we're probably ok to handle it
            if (e.target.nodeName === 'TEXTAREA') { return; }
            return this.handleKeyDown(e);
        }).bind(this));
    },
    handleScroll: function (e) {
        var steps = this.getDOMNode().querySelectorAll('#mainsteps > .step');
        var offsets = [].map.call(steps, function (e) { return e.children[0].scrollTop; });
        var ss = this.state.stepScroll;
        if (offsets.some(function(v, i) { return v !== ss[i]; })) {
            this.setState({'stepScroll': offsets});
        }
    },
    componentWillReceiveProps: function (nextProps) {
        this.setState({'stepIdx': 0});
    },
    getInitialState: function () {
        return {'stepIdx': 0, 'stepScroll': [0, 0, 0], 'miniStepsOnly': false};
    },
    render: function () {
        var stepIdx = this.state.stepIdx;
        var stepElts = [];
        var miniStepElts = [];
        this.props.steps.map(function (step, si) {
            var className = 'step';
            if (stepIdx === si) { className += ' selected-step'; }
            var elt = (
                <div className={className} key={'step'+(si)}>
                    <DecompileStepCode step={step} />
                </div>
            );
            miniStepElts.push(elt);
            if (si < stepIdx - 1 || si > stepIdx + 1) { return; }
            stepElts.push(elt);
        }, this);
        // Add blank divs at beginning or end
        if (stepElts.length === 2) {
            var span;
            if (stepElts[0].key !== 'step'+(stepIdx-1)) {
                span = (<span className='commentary'>
                    On the left is the code to decompile.
                    <p />
                    However, first it must be compiled.
                    Immediately on the right is the result of passing the code to the Tcl
                    bytecode (BC) compiler as a proc body. Lines like
                    `<span className='code'>&lt;X: text (params)&gt;</span>` are a
                    human-readable representation of each 'instruction' produced by the
                    BC compiler - on execution they'd be run by the Tcl BC
                    interpreter in a <a href='http://en.wikipedia.org/wiki/Stack_machine'>stack machine</a>,
                    somewhat like Java (and Python).
                    <p />
                    For example, `<span className='code'>&lt;30: push1 (2)&gt;</span>` will
                    push the second value from the 'literals array' onto the
                    stack. If you're interested in learning more,
                    `<a href='https://github.com/tcltk/tcl/blob/core_8_5_16/generic/tclCompile.c#L41'><span className='code'>tclCompile.h</span></a>`
                    has a list of BC instructions and
                    `<a href='https://github.com/tcltk/tcl/blob/core_8_5_16/generic/tclCompile.h#L345'><span className='code'>tclCompile.c</span></a>`
                    details what a 'bytecode' structure looks like.
                    <p />
                    When you move across, you can see `<span className='code'>tcldis</span>`
                    at work turning the BC instructions back into readable Tcl code.
                    Anything marked with `<span className='code'>{'\u00bb'}</span>` represents
                    a value on the stack, i.e. it still needs to be 'consumed' by something.
                    <br />
                    The ministeps view (up and down) is just a zoomed out way of seeing how
                    decompilation progresses.
                    <p />
                    Note: `<span className='code'>tcldis</span>` is not complete! It recognises
                    a limited set of patterns for a limited set of instructions
                    and is developed against a single version of Tcl. However, it does have a
                    set of <a href='https://github.com/aidanhs/tcldis/blob/master/tests/test.py'>test cases</a> which
                    are verified as being decompilable.
                </span>);
                stepElts.unshift(<div className='step' key={'step'+(stepIdx-1)}>{span}</div>);
            } else if (stepElts[1].key !== 'step'+(stepIdx+1)) {
                span = (<span className='commentary'>
                    Your decompiled (as much as possible) code is on the left.
                    <br />
                </span>);
                stepElts.push(<div className='step' key={'step'+(stepIdx+1)}>{span}</div>);
            }
        }

        // Add the step padding
        stepElts.splice(1, 0,
            <StepPadding key={'pad'+(stepIdx-1)}
            stepIdx={stepIdx-1} steps={this.props.steps} changes={this.props.changes}
            offsets={this.state.stepScroll.slice(0, 2)}
            />
        );
        stepElts.splice(3, 0,
            <StepPadding key={'pad'+(stepIdx)}
            stepIdx={stepIdx} steps={this.props.steps} changes={this.props.changes}
            offsets={this.state.stepScroll.slice(1, 3)}
            />
        );

        // Fold up the main steps if we're not displaying them
        var mainstepsstyle = this.state.miniStepsOnly ? {'height': 0, 'opacity': 0} : {};

        // Put the selected ministep halfway along the bottom
        var halfway = -((stepIdx * miniwidth) + (miniwidth / 2));
        var ministepsstyle = {'left': halfway + 'px'};

        return (
            <div id='stepsarea'>
                <div id='mainsteps' style={mainstepsstyle} onScroll={this.handleScroll}>{stepElts}</div>
                <div id='ministeps' style={ministepsstyle}>{miniStepElts}</div>
            </div>
        );
    }
});

window.TclDisUI = React.createClass({
    getInitialState: function () {
        return {'steps': [], 'changes': []};
    },
    getDecompileSteps: function (code) {
        window.getDecompileSteps(code, function (err, data) {
            this.setState(data);
        }.bind(this));
    },
    render: function () {
        return (
            <div>
                <ActionArea decompileCB={this.getDecompileSteps} />
                <DecompileSteps steps={this.state.steps} changes={this.state.changes} />
            </div>
        );
    }
});
})();
