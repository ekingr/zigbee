// rules.jsx
//
// Utils
// API
// StateDisplay
// StateEditor
// RulesList
// RuleEditor
// Main component
//
//
// One main page with either component:
//  a- list view of all rules
//  b- edit view of a specific rule
//
// At stratupt, main component:
//  - loads data
//
// StateDisplay: View current state
//  - displays the current status
//  - allows to switch view to StateEditor
//  - allows to switch view to RulesList
//
// StateEditor: Change current state
//  - displays a form to change state of devices
//  - saves changes to API
//  - triggers a refresh after committing and go back to StateDisplay
//  - allows to switch view back to StateDisplay (abort)
//
// RulesList: View list of rules
//  - displays the rules
//  - allows to select which rule to edit: switch view to RuleEditor
//  - allows to swutch view to StateDisplay
//  - allows for some quick edits: reordering & enhabling/disabling of rules
//
// RuleEditor: Edit a rule
//  - displays a form to create / edit rule
//  - edit also allows to see details not shown in the list view
//  - saves changes to API (add/update/delete)
//  - triggers a refresh after committing (to update list)


// Utils //////////////////////////////////////////////////////////////////////

/* Custom Date class */
class MyDate extends Date {
    // Constructor: Parsing Golang date format (eg. "2023-09-12T19:30:00Z")
    // slicing any elements not understood by JS (sometimes TZ info after char #23)
    // and adjusting for UTC (golang in UTC, JS parsing in local)
    constructor (goDate) {
        if (goDate) {
            super(goDate.slice(0,23));
        } else {
            super();
        }
        this.setMinutes(this.getMinutes() - this.getTimezoneOffset());
    }
    // HTML format for `datetime-local` input (eg. "2023-09-12 21:30"), trunctated to minutes
    toHTML = () =>
        this.toISOString().slice(0,16);
    // Time format display (eg. "02:00")
    toTimeFormat = () =>
        this.toISOString().substr(11,5);
}

/* Build className string based on properties object */
function classSet(classes) {
    let classNames = [];
    for (const cn in classes) {
        if (classes[cn]) {
            classNames.push(cn);
        }
    }
    return classNames.join(' ');
}


// API ////////////////////////////////////////////////////////////////////////

const API = {
    _root: '/api/zigbee',
    // Get state (and rules & devices)
    getState: () => {
        return fetch(API._root + '/status.json', {
            method: 'GET',
        }).then(r => {
            if (!r.ok) {
                console.error('API error getting state: ' + r.status + ' ' + r.statusText);
                return {apiOk: false, apiStatusCode: r.status, apiStatus: r.statusText, apiTime: Date.now()};
            }
            return r.json().then(j => ({...j, apiOk: true, apiStatusCode: r.status, apiStatus: r.statusText, apiTime: Date.now()}));
        });
    },
    // Set state
    setState: state => {
        return fetch(API._root + '/setState', {
            method: 'POST',
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: JSON.stringify({state: state}),
        }).then(r => r.text().then(txt => ({
            apiOk: r.ok,
            apiStatusCode: r.status,
            apiStatus: r.statusText,
            apiResponse: txt,
            apiTime: Date.now()
        })));
    },
    // Set rules
    setRules: rules => {
        return fetch(API._root + '/setRules', {
            method: 'POST',
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: JSON.stringify({rules: rules}),
        }).then(r => r.text().then(txt => ({
            apiOk: r.ok,
            apiStatusCode: r.status,
            apiStatus: r.statusText,
            apiResponse: txt,
            apiTime: Date.now()
        })));
    },
};


// StateDisplay: View current state ///////////////////////////////////////////
class StateDisplay extends React.Component {
    constructor(props) {
        // props = {
        //   data: {},
        //   edit: () => (),
        //   rules: () => (),
        // }
        super(props);
        this.state = {
        };
    }
    rules = (evt) => {
        evt?.preventDefault();
        this.props.rules();
    }
    edit = (evt) => {
        evt?.preventDefault();
        this.props.edit();
    }
    render = () => {
        const devices = this.props.data.devices.filter(d => d.id in this.props.data.zigbee).map(d => {
            let statusTxt = 'na';
            let statusCls = '';
            switch (this.props.data.zigbee[d.id]) {
                case 1:
                    statusTxt = 'ON';
                    statusCls = 'isOn';
                    break;
                case 0:
                    statusTxt = 'OFF';
                    statusCls = 'isOff';
                    break;
                case -1:
                    statusTxt = 'out';
                    statusCls = 'isOut';
                    break;
            }
            return (
                <div key={d.id}>
                    <div className='device'>
                        <span title={d.id}>{d.name}</span>
                    </div>
                    <div className={'status ' + statusCls}>
                        {statusTxt}
                    </div>
                </div>
            );
        });
        return (<>
            <nav>
                <span />
                <button onClick={this.rules} className='action submit'>Règles {'\u003e'}</button>
            </nav>
            <nav>
                <h2>Status</h2>
            </nav>
            <section className='devices'>
                {devices}
            </section>
            <nav>
                <span />
                <button onClick={this.edit} className='action submit'>Modifier</button>
            </nav>
        </>);
    }
}


// StateEditor: Change current state //////////////////////////////////////////
class StateEditor extends React.Component {
    constructor(props) {
        // props = {
        //   data: {},
        //   cancel: () => (),
        //   submit: (state) => (),
        // }
        super(props);
        this.state = {
        };
        this.refDSet = {};
        this.props.data.devices?.forEach(device => {
            this.refDSet[device.id] = React.createRef();
        });
    }
    cancel = (evt) => {
        evt?.preventDefault();
        this.props.cancel();
    }
    submit = (evt) => {
        evt?.preventDefault();
        let newState = {};
        for (const d in this.props.data.zigbee) {
            newState[d] = this.refDSet[d].current.checked ? 1 : 0;
        }
        this.props.submit(newState);
    }
    render = () => {
        const devices = this.props.data.devices.filter(d => d.id in this.props.data.zigbee).map(d => {
            let statusTxt = 'na';
            let statusCls = '';
            switch (this.props.data.zigbee[d.id]) {
                case 1:
                    statusTxt = 'ON';
                    statusCls = 'isOn';
                    break;
                case 0:
                    statusTxt = 'OFF';
                    statusCls = 'isOff';
                    break;
                case -1:
                    statusTxt = 'out';
                    statusCls = 'isNovo';
                    break;
            }
            return (
                <div key={d.id}>
                    <div className='device'>
                        <span title={d.id}>{d.name}</span>
                    </div>
                    <div>
                        <input type='checkbox' defaultChecked={this.props.data.zigbee[d.id]==1} ref={this.refDSet[d.id]} className='switch' id={'s_'+d.id} name={'s_'+d.id} />
                        <label htmlFor={'s_'+d.id} />
                    </div>
                </div>
            );
        });
        return (<>
            <nav>
                <button onClick={this.cancel} className='action back'>{'\u003c'} Annuler</button>
            </nav>
            <nav>
                <h2>Status</h2>
            </nav>
            <section className='devices'>
                {devices}
            </section>
            <nav>
                <span />
                <button onClick={this.submit} className='action submit'>Valider</button>
            </nav>
        </>);
    }
}


// RulesList: View list of rules //////////////////////////////////////////////
class RulesList extends React.Component {
    constructor(props) {
        // props = {
        //   data: {},
        //   rule: 0,
        //   selectRule: (ruleId) => (),
        //   submit: (rules) => (),
        //   state: () => (),
        // }
        super(props);
        this.state = {
        };
    }
    gotoState = (evt) => {
        evt?.preventDefault();
        this.props.state();
    }
    selectRule = (i) => {
        return (evt) => {
            evt?.preventDefault();
            this.props.selectRule(i);
        };
    }
    newRule = (evt) => {
        evt?.preventDefault();
        this.props.selectRule(-1);
    }
    moveUp = (i) => {
        return (evt) => {
            evt?.preventDefault();
            console.log('Move up', i);
            if (i < 1) {
                return;
            }
            const rules = this.props.data.rules;
            const acc = rules[i-1];
            rules[i-1] = rules[i];
            rules[i] = acc;
            this.props.submit(rules);
        };
    }
    toggle = (i) => {
        return (evt) => {
            console.log('Toggle', i, evt.target.checked);
            this.props.data.rules[i].enabled = evt.target.checked;
            this.props.submit(this.props.data.rules);
        };
    }
    render = () => {
        let ruleId = this.props.rule;
        if (ruleId > this.props.data?.rules.length - 1) {
            ruleId = this.props.data?.rules.length > 0 ? 0 : -1;
        }
        const opts = [].concat(this.props.data?.rules.length > 0 ? this.props.data?.rules : []);
        const rules = opts.map((r, i) => (
            <div key={i}>
                <div className='rule'>
                    <button onClick={this.moveUp(i)} disabled={i==0} title='Remonter'>
                        <i>{'\u2303'}</i>
                    </button>
                    <a onClick={this.selectRule(i)} tabIndex='1'>{r.name}</a>
                    <span className='info'>{new MyDate(r.timestamp).toTimeFormat()}</span>
                </div>
                <div>
                    <input type='checkbox' className='switch enab' defaultChecked={r.enabled} id={'enab_r'+i} onChange={this.toggle(i)} />
                    <label htmlFor={'enab_r'+i} />
                </div>
            </div>
        ));
        return (<>
            <nav>
                <button onClick={this.gotoState} className='action back'>{'\u003c'} Status</button>
            </nav>
            <nav>
                <h2>Règles</h2>
            </nav>
            <section className='rules'>
                {rules}
            </section>
            <nav>
                <button onClick={this.newRule} className='action new'>{'\u2295'} Nouvelle règle</button>
            </nav>
        </>);
    }
}


// RuleEditor: Edit a rule ////////////////////////////////////////////////////
class RepeatEditor extends React.Component {
    constructor(props) {
        // props = {
        //   defaultValue: 0, // minutes
        // }
        super(props);
        this.state = {
        };
        this.refM = React.createRef();
        this.refH = React.createRef();
        this.refD = React.createRef();
    }
    value = () => {
        const d = parseInt(this.refD.current.value) || 0;
        const h = parseInt(this.refH.current.value) || 0;
        const m = parseInt(this.refM.current.value) || 0;
        return ((d * 24) + h) * 60 + m;
    }
    render = () => {
        const mm = this.props.defaultValue;
        const m = mm % 60;
        const hh = (mm - m) / 60;
        const h = hh % 24;
        const d = (hh - h) / 24;
        return (<span className='reptInput'>
            <input type='number' step='1' min='0' max='366' defaultValue={d} ref={this.refD} id='reptD' />
            <label htmlFor='reptD'>d</label>
            <input type='number' step='1' min='0' max='24' defaultValue={h} ref={this.refH} id='reptH' />
            <label htmlFor='reptH'>h</label>
            <input type='number' step='1' min='0' max='60' defaultValue={m} ref={this.refM} id='reptM' />
            <label htmlFor='reptM'>min</label>
        </span>);
    }
}

class RuleEditor extends React.Component {
    constructor(props) {
        // props = {
        //   data: {},
        //   rule: 0,
        //   submit: (rule) => (),
        //   cancel: () => (),
        // }
        super(props);
        this.state = {
            rule: this.dataToRepr(),
        };
        this.refName = React.createRef();
        this.refEnab = React.createRef();
        this.refTsmp = React.createRef();
        this.refRept = React.createRef();
        this.refDSet = {};
        this.props.data.devices?.forEach(device => {
            this.refDSet[device.id] = React.createRef();
        });
    }
    componentDidUpdate = (prevProps) => {
        if (prevProps.rule != this.props.rule
            || prevProps.data?.apiTime != this.props.data?.apiTime) {
            // Update has been performed, we can scrap the current values
            this.props.data.devices?.forEach(device => {
                if (! (device.id in this.refDSet)) {
                    this.refDSet[device.id] = React.createRef();
                };
            });
            this.setState({rule: this.dataToRepr()});
        }
    }
    dataToRepr = () => {
        if (this.props.rule > (this.props.data.rules?.length || 0) - 1) {
            throw 'Invalid rule id';
        }
        const rule = this.props.rule >= 0 ? this.props.data.rules[this.props.rule] : {
            name: '',
            enabled: 0,
            timestamp: '',
            repeat: 0,
            newState: {},
        };
        rule._timestamp = new MyDate(rule.timestamp).toHTML();
        rule._repeat = rule.repeat / 60e9; // ns->min
        // Skipping conversion of newState int to bool which works okay.
        return rule
    }
    reprToData = () => {
        const rule = {
            name: this.refName.current.value,
            enabled: this.refEnab.current.checked,
            timestamp: (new Date(this.refTsmp.current.value)).toISOString(),
            repeat: this.refRept.current.value() * 60e9, // min->ns
            newState: {},
        };
        this.props.data.devices?.forEach(device => {
            if (device.id in this.state.rule.newState) {
                rule.newState[device.id] = this.refDSet[device.id].current.checked ? 1 : 0;
            };
        });
        return rule;
    }
    addDevice = (dId) => {
        return (evt) => {
            evt?.preventDefault();
            const newRule = this.state.rule;
            newRule.newState[dId] = false;
            this.setState({rule: newRule});
        };
    }
    removeDevice = (dId) => {
        return (evt) => {
            evt?.preventDefault();
            const newRule = this.state.rule;
            delete newRule.newState[dId];
            this.setState({rule: newRule});
        };
    }
    submit = (evt) => {
        evt?.preventDefault();
        const rule = this.reprToData();
        console.log('Save:', rule);
        this.props.submit(rule);
    }
    deleteRule = (evt) => {
        evt?.preventDefault();
        console.log('Delete');
        this.props.submit(null);
    }
    cancel = (evt) => {
        evt?.preventDefault();
        console.log('Cancel');
        this.props.cancel();
    }
    render = () => {
        let usedDevices = [];
        let unUsedDevices = [];
        for (const device of this.props.data.devices) {
            if (device.id in this.state.rule.newState) {
                usedDevices.push((<div key={device.id}>
                    <div className='device'>
                        <button onClick={this.removeDevice(device.id)} title='Remove'>
                            <i>{'\u2013'}</i>
                        </button>
                        <span title={device.id}>{device.name}</span>
                    </div>
                    <div>
                        <input type='checkbox' className='switch' ref={this.refDSet[device.id]} defaultChecked={this.state.rule.newState[device.id]} id={'enab_'+device.id} />
                        <label htmlFor={'enab_'+device.id} />
                    </div>
                </div>));
            } else {
                unUsedDevices.push((<div key={device.id}>
                    <div className='device'>
                        <button onClick={this.addDevice(device.id)} title='Add'>
                            <i>+</i>
                        </button>
                        <span title={device.id}>{device.name}</span>
                    </div>
                    <div>
                    </div>
                </div>));
            }
        }
        const newState = (this.props.data.devices || []).flatMap(device => {
            if (! (device.id in this.state.rule.newState)) {
                return [];
            }
        });
        return (<>
            <nav>
                <button onClick={this.cancel} className='action back'>{'\u003c'} Annuler</button>
                <button onClick={this.submit} className='action submit'>Valider</button>
            </nav>

            <section className='descr'>
                <div className='name'>
                    <input type='text' ref={this.refName} defaultValue={this.state.rule.name} placeholder='Nom de la règle' />
                </div>
                <div className='enab'>
                    <input type='checkbox' className='switch enab' ref={this.refEnab} defaultChecked={this.state.rule.enabled} id='enab' />
                    <label htmlFor='enab' />
                </div>
                <div className='tsmp'>
                    <label htmlFor='tmsp' className='label'>Exécuter : </label>
                    <input type='datetime-local' ref={this.refTsmp} defaultValue={this.state.rule._timestamp} id='tmsp' step='60' /><br />
                </div>
                <div className='rept'>
                    <span className='label'>Répéter : </span>
                    <RepeatEditor ref={this.refRept} defaultValue={this.state.rule._repeat} />
                </div>
            </section>

            {usedDevices.length > 0 &&
            <section className='devices used'>
                {usedDevices}
            </section>
            }

            {unUsedDevices.length > 0 &&
            <section className='devices unused'>
                {unUsedDevices}
            </section>
            }

            <nav>
                <button onClick={this.deleteRule} className='action del'>Supprimer</button>
            </nav>
        </>);
    }
}


// Main component /////////////////////////////////////////////////////////////
const VIEW_STATE_SHOW = 'VIEW_STATE_SHOW';
const VIEW_STATE_EDIT = 'VIEW_STATE_EDIT';
const VIEW_RULES_LIST = 'VIEW_RULES_LIST';
const VIEW_RULES_EDIT = 'VIEW_RULES_EDIT';
class App extends React.Component {
    constructor(props) {
        // props = {}
        super(props);
        this.state = {
            view: VIEW_STATE_SHOW, // View to display
            error: '', // Is in error state while not null
            loading: 'Initialisation...', // Is in loading state while not null
            data: null, // State data from API
            rule: -1, // Current rule to edit (-1 for new one)
        };
        this.firstLoad = true;
    }
    componentDidMount = () => {
        this.refresh();
    }
    refresh = () => {
        this.setState({loading: 'Téléchargement des règles...', error: null});
        return API.getState().then(apist => {
            console.log(apist);
            if (! apist.apiOk) {
                this.setState({
                    error: 'Erreur lors du chargement : #' + apist.apiStatusCode + ' ' + apist.apiStatus,
                    loading: null,
                    data: apist,
                });
                return null;
            }
            let rule = this.state.rule;
            if (this.firstLoad || rule > apist.rules.length - 1) {
                this.firstLoad = false;
                rule = apist.rules.length > 0 ? 0 : -1;
            }
            this.setState({
                loading: null,
                error: null,
                data: apist,
                rule: rule
            });
            return apist;
        });
    }
    // Submit state changes to the API
    submitState = (state) => {
        console.log('SubmitState:', state);
        this.setState({loading: 'Enregistrement des modifications...', error: null});
        return API.setState(state).then(apist => {
            console.log(apist);
            if (! apist.apiOk) {
                this.setState({
                    error: 'Erreur lors de l\'enregistrement : #' + apist.apiStatusCode + ' ' + apist.apiStatus + ' (' + apist.apiResponse + ')',
                    loading: null,
                });
                return;
            }
            return;
        }).then(r => this.refresh()).then(r => {
            this.setState({view: VIEW_STATE_SHOW});
        });
    }
    // Internal function to sumbit rules changes to API
    _submitRules = (rules) => {
        this.setState({loading: 'Enregistrement des modifications...', error: null});
        console.log('Saving:', rules);
        return API.setRules(rules).then(apist => {
            console.log(apist);
            if (! apist.apiOk) {
                this.setState({
                    error: 'Erreur lors de l\'enregistrement : #' + apist.apiStatusCode + ' ' + apist.apiStatus + ' (' + apist.apiResponse + ')',
                    loading: null,
                });
                return;
            }
            // Do NOT set new state, as ruleid may be wrong at that point.
            // state will be updated anyways at refresh right after.
            //this.setState({loading: null, error: null});
            return;
        }).then(r => (this.refresh()));
    }
    // Submitting changes to the list of rules (by viewer)
    submitRules = (rules) => {
        console.log('SubmitRules:', rules);
        return this._submitRules(rules);
    }
    // Submitting changes to a single rule (by editor)
    submitRule = (rule) => {
        let rules = this.state.data.rules || [];
        let rId = this.state.rule
        if (this.state.rule == -1) {
            // New rule
            rules.push(rule);
            rId = rules.length - 1;
        } else if (! rule) {
            // Delete rule
            rules.splice(this.state.rule, 1);
            rId = rId - 1;
        } else {
            // Modify existing rule
            rules[this.state.rule] = rule;
        }
        return this._submitRules(rules).then(apist => {
            // If just deleted a rule, go back to the list view
            this.setState({
                rule: rId,
                view: (! rule) ? VIEW_RULES_LIST : this.state.view,
            });
        });
    }
    // Switch view, aborting any pending changes
    _switchView = (view) => {
        this.refresh().then(apist => {
            if (!apist || this.state.error) {
                return;
            }
            this.setState({
                view: view,
            });
        });
    }
    viewStateShow = () => this._switchView(VIEW_STATE_SHOW)
    viewStateEdit = () => this._switchView(VIEW_STATE_EDIT)
    viewRulesList = () => this._switchView(VIEW_RULES_LIST)
    // Switch view to EDIT
    selectRule = (ruleId) => {
        this.refresh().then(apist => {
            if (!apist || this.state.error) {
                return;
            }
            if (ruleId > apist.rules.length - 1) {
                ruleId = apist.rules.length > 0 ? 0 : -1;
            }
            this.setState({
                view: VIEW_RULES_EDIT,
                rule: ruleId,
            });
        });
    }
    render = () => {
        if (this.state.error) {
            if (this.state.data?.apiStatusCode == 403) {
                // Unauthorized
                return (<p>Please <a href='/login.html'>log in</a></p>);
            }
            return (<p className='err'>{this.state.error}</p>);
        }
        if (this.state.loading) {
            return (<p>{this.state.loading}</p>);
        }
        switch (this.state.view) {
            case VIEW_STATE_SHOW:
                return (<StateDisplay data={this.state.data} edit={this.viewStateEdit} rules={this.viewRulesList} />);
            case VIEW_STATE_EDIT:
                return (<StateEditor data={this.state.data} cancel={this.viewStateShow} submit={this.submitState} />);
            case VIEW_RULES_LIST:
                return (<RulesList data={this.state.data} rule={this.state.rule} selectRule={this.selectRule} submit={this.submitRules} state={this.viewStateShow} />);
            case VIEW_RULES_EDIT:
                return (<RuleEditor data={this.state.data} rule={this.state.rule} submit={this.submitRule} cancel={this.viewRulesList} />);
            default:
                throw 'Invalid view state';
        }
    }
}
const app = ReactDOM.render(<App />, document.getElementById('main'));
