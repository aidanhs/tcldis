(function () {
'use strict';
var miniwidth = 80;
var padwidth = 50;
var linemult = 1.25;
var fontsize = 12 * linemult;

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
        return (
            <div id='actionarea'>
                <div><div id='actionbuttons'>
                    <div><button onClick={this.onDecompileClick}>Decompile!</button></div>
                    <div><button onClick={this.helpMe}>Help!</button></div>
                </div></div>
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
                cs = c[0], // What step is this change transforming?
                cb = c[1], // What block is this change transforming?
                ss = steps;

            numlines = 0;
            bbi = 0; // Which bblock are we looking at right now
            ii = 0; // Which 'line' in the bblock are we looking at right now
            step = ss[cs];
            var starty1, starty2;
            // Find the offset of source lines
            while (true) {
                if (bbi === cb && ii === c[2][0]) {
                    starty1 = numlines;
                }
                if (bbi === cb && ii === c[2][1]) {
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
                if (bbi === cb && ii === c[3][0]) {
                    endy1 = numlines;
                }
                if (bbi === cb && ii === c[3][1]) {
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
            var step = c[0];
            if (c[0] !== stepIdx) {
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
                return (
                    <span key={bbi}>{bb.map(function (inst, ii) {
                        return <span key={ii}>{inst+'\n'}</span>;
                    })}</span>
                );
            })}</pre>
        );
    }
});

var DecompileSteps = React.createClass({
    handleKeyDown: function (e) {
        var key = e.keyCode || e.charCode;
        var stepIdx = this.state.stepIdx;
        // 37 <-, 38 ^, 39 ->, 40 \/
        if (key === 37) { this.changeStepIdx(-1); }
        else if (key === 38) { this.showMiniSteps(true); }
        else if (key === 39) { this.changeStepIdx(1); }
        else if (key === 40) { this.showMiniSteps(false); }
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
    },
    componentDidMount: function () {
        document.addEventListener('keydown', (function (e) {
            // Is this an event that was fired on us?
            var target = e.target;
            if (target != document && target != document.body) {
                while (target.parentNode != document.body) {
                    target = target.parentNode;
                }
                if (target != this.getDOMNode()) { return; }
            }
            return this.handleKeyDown(e);
        }).bind(this));
    },
    handleScroll: function (e) {
        var steps = this.getDOMNode().querySelectorAll('#mainsteps > .step > pre');
        var offsets = [].map.call(steps, function (e) { return e.scrollTop; });
        var ss = this.state.stepScroll;
        if (offsets.some(function(v, i) { return v !== ss[i]; })) {
            this.setState({'stepScroll': offsets});
        }
    },
    componentWillReceiveProps: function (nextProps) {
        var stepIdx = nextProps.steps.length - 2;
        if (stepIdx < 0) { stepIdx = 0; }
        this.setState({'stepIdx': stepIdx});
    },
    getInitialState: function () {
        return {'stepIdx': 0, 'stepScroll': [0, 0, 0], 'miniStepsOnly': false};
    },
    render: function () {
        var stepIdx = this.state.stepIdx;
        var steps = [];
        var ministeps = [];
        this.props.steps.map(function (step, si) {
            var stepslist = steps;
            var className = 'step';
            if (stepIdx === si) { className += ' selected-step'; }
            var elt = (
                <div className={className} key={si}>
                    <DecompileStepCode step={step} />
                </div>
            );
            ministeps.push(elt);
            if (si < stepIdx - 1 || si > stepIdx + 1) { return; }
            steps.push(elt);
        }, this);
        // Add blank divs at beginning and end
        if (steps.length === 2) {
            if (steps[1].props.key != stepIdx + 1) {
                steps.push(<div className='step' key={stepIdx + 1}><pre> </pre></div>);
            } else if (steps[0].props.key != stepIdx - 1) {
                steps.unshift(<div className='step' key={stepIdx - 1}><pre> </pre></div>);
            }
        }

        // Add the step padding
        steps.splice(1, 0,
            <StepPadding key={'pad'+(stepIdx)}
            stepIdx={stepIdx - 1} steps={this.props.steps} changes={this.props.changes}
            offsets={this.state.stepScroll.slice(0, 2)}
            />
        );
        steps.splice(3, 0,
            <StepPadding key={'pad'+(stepIdx+1)}
            stepIdx={stepIdx} steps={this.props.steps} changes={this.props.changes}
            offsets={this.state.stepScroll.slice(1, 3)}
            />
        );

        // Fold up the main steps if we're not displaying them
        var mainstepsstyle = {'transition': 'height 0.5s, opacity 0.5s'};
        if (this.state.miniStepsOnly) {
            mainstepsstyle.height = '0';
            mainstepsstyle.opacity = '0';
        }

        // Put the selected ministep halfway along the bottom
        var halfway = -((stepIdx * miniwidth) + (miniwidth / 2));
        var ministepsstyle = {
            'transition': 'left 0.2s',
            'left': halfway + 'px'
        };
        return (
            <div id='stepsarea'>
                <div id='mainsteps' style={mainstepsstyle} onScroll={this.handleScroll}>{steps}</div>
                <div id='ministeps' style={ministepsstyle}>{ministeps}</div>
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
