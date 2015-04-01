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
    onHelpButtonToggle: function () {
        this.setState({'helpVisible': !this.state.helpVisible});
    },
    render: function () {
        var kdFire = function (keycode) {
           return function () {
               // Actual KeyboardEvent is broken in Chrome...
               // http://stackoverflow.com/questions/1897333/firing-a-keyboard-event-on-chrome
               var e = new Event('keydown');
               e.keyCode = keycode;
               document.dispatchEvent(e);
           };
        };
        if (this.state.helpVisible) {
            return (
                <div id='helparea'><div style={{'max-width': '800px', 'margin': '0 auto'}}>
                    <button id='helpbutton' onClick={this.onHelpButtonToggle}>Hide Info</button>
                    <span className='commentary'>
                        <u>What is it?</u>
                        <br />
                        TclDis was created when I was learning about Tcl
                        bytecode. I'm fairly interested in decompilers so decided to
                        to create a tool that (I believe) didn't exist, which would take
                        some Tcl bytecode and output the Tcl code that compiled to it. I assume
                        the only reason it's never been done for Tcl is the size of the
                        community - both Python and Java have a number of tools like TclDis.
                        <p />
                        <u>Where's the code?</u>
                        <br />
                        On <a href='https://github.com/aidanhs/tcldis/'>GitHub</a>.
                        Decompilation happens in a single ~1000 line Python
                        file. C is used to extract
                        information from the Tcl interpreter, and could be mostly
                        replaced with `<span className='code'><a href='http://wiki.tcl.tk/40936'>getbytecode</a></span>`
                        (which didn't exist when tcldis was created). React and JavaScript is used
                        to create this web interface.
                        <br />
                        It's worth noting that the decompliation works based on patterns. This
                        is a very simple (but inflexible) method of decompliation and becomes a
                        pain when optimisers get clever and move instructions around.
                        <p />
                        <u>https://aidanhs.github.io/tcldis loads very slowly!</u>
                        <br />
                        Because TclDis uses Python, Tcl and C, it would usually be a server side
                        application. But I wanted to host the whole project on GitHub pages with
                        no external dependencies. By combining three of my other projects
                        (<a href='https://github.com/aidanhs/libtclpy'>libtclpy</a>, <a href='https://github.com/aidanhs/empython'>empython</a> and <a href='https://github.com/aidanhs/emtcl'>emtcl</a>)
                        and <a href='https://github.com/kripken/emscripten'>Emscripten</a> in
                        a very <a href='https://github.com/aidanhs/tcldis/blob/gh-pages/script.sh'>particular</a> way,
                        you get a Tcl decompiler in pure JS. Why so slow?
                        You're actually running full Tcl and Python interpreters in the browser!
                        <br />
                        It's probably worth repeating that - Emscripten allows you to put
                        together a Python and Tcl interpreter, a C extension to let them talk
                        to each other, the entire Python standard library and the TclDis code
                        itself in under 12MB. I think that's pretty good.
                        <br />
                        If you want to play with this, run:
                        <br />
                        <span className='code'>empython.eval('import tclpy');<br />
                        empython.eval('tclpy.eval("puts [list 1 2 3]")');</span>
                        <br />
                        in your JavaScript console.
                        <p />
                        <u>There's a bug! Will you fix it?</u>
                        <br />
                        If causes a crash, possibly. Otherwise (e.g. recognising
                        new instructions) probably not.
                        <p />
                        <u>Can I decompile .tbc files?</u>
                        <br />
                        In theory, but no support will be offered.
                    </span>
                </div></div>
            );
        }
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
                    <button id='helpbutton' onClick={this.onHelpButtonToggle}>Tell me more about TclDis!</button>
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
                ss = steps;

            if (c.tag === 'block_join' || c.tag === 'block_rm') {
                var text = 'Internal rearrangement ';
                text += c.tag === 'block_join' ? '(bblock joining)' : '(bblock elimination)';
                var style = {'fontSize': 12, 'fontFamily': 'monospace'};
                var x = 20, y = (-2.5*padwidth) + (0.25*style.fontSize);
                return [
                    <text key={1} x={x} y={y} transform='rotate(90)' style={style}>{text}</text>
                ];
            }

            numlines = 0;
            bbi = 0; // Which bblock are we looking at right now
            ii = 0; // Which 'line' in the bblock are we looking at right now
            step = ss[cs];
            var starty1, starty2;
            // Find the offset of source lines
            while (true) {
                if (bbi === c.from[0][0] && ii === c.from[0][1]) {
                    starty1 = numlines;
                }
                if (bbi === c.from[1][0] && ii === c.from[1][1]) {
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
                if (bbi === c.to[0][0] && ii === c.to[0][1]) {
                    endy1 = numlines;
                }
                if (bbi === c.to[1][0] && ii === c.to[1][1]) {
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
        if (stepIdx < 0 || stepIdx >= this.props.steps.length) {
            return;
        }
        // Drop the offset of the step that will be removed.
        var i;
        var offsets = this.state.stepScroll.slice();
        for (i = 0; i < idxChange; i++) {
            offsets.splice(0, 1);
            offsets.push(0);
        }
        for (i = 0; i > idxChange; i--) {
            offsets.splice(-1, 1);
            offsets.unshift(0);
        }
        this.setState({
            'stepIdx': stepIdx,
            'stepScroll': offsets
        });
    },
    componentDidMount: function () {
        document.addEventListener('keydown', (function (e) {
            // If it's not fired on the textarea, we're probably ok to handle it
            if (e.target.nodeName === 'TEXTAREA') { return; }
            return this.handleKeyDown(e);
        }).bind(this));
    },
    componentDidUpdate: function () {
        var steps = this.getDOMNode().querySelectorAll('#mainsteps > .step');
        var offsets = this.state.stepScroll;
        [].forEach.call(steps, function (e, i) {
            e.children[0].scrollTop = offsets[i];
        });
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
        this.setState(this.getInitialState());
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
            if (err) {
                alert('Looks like that decompilation failed, see the console for details');
                console.log(data);
                this.setState(this.getInitialState());
                return;
            }
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
