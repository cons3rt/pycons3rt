def ipt_flush(self):
    log = logging.getLogger(self.cls_logger + '.ipt_flush')
    # TODO: Find all chains, flush. Also, move into pycons3rt.
    try:
        self.in_chain.flush()
        self.out_chain.flush()
        self.fwd_chain.flush()
        self.pre_chain.flush()
        self.post_chain.flush()
        log.info('Flushed iptables.')
    except Exception as e:
        log.error('Failed to flush iptables: {}'.format(str(e)))

def add_rule(self,source=None,int=None,dport=None,sport=None,table=None,
    proto=None,chain=None):
    log = logging.getLogger(self.cls_logger + '.masq')
    #TODO

def masq(self,source=None,out_interface=None):
    log = logging.getLogger(self.cls_logger + '.masq')
    try:s
        rule = iptc.Rule()
        rule.source = source
        rule.out_interface = out_interface
        target = iptc.Target(rule, 'MASQUERADE')
        rule.target = target
        self.post_chain.insert_rule(rule)
        log.info('MASQ rule enabled. Source range: {} out interface: {}'.format(source,out_interface))
    except Exception as e:
        log.error('Failed to add MASQ rule. Source: {}. Int: {}. Error: {}'.format(source,
            out_interface,str(e)))

def redirect_port(self,dport=None,to_port=None,source=None):
    log = logging.getLogger(self.cls_logger + '.redirect_port')
    # configure pre-routing rule for 80->atlassian mapping
    try:
        rule = iptc.Rule()
        rule.protocol = 'tcp'
        match = iptc.Match(rule, 'tcp')
        match.dport = dport
        rule.add_match(match)
        target = iptc.Target(rule,'REDIRECT')
        target.to_ports = to_port
        rule.target = target
        self.pre_chain.insert_rule(rule)
        log.info('Added prerouting rule. DPORT {} redirects to {}.'.format(dport,to_port))
    except Exception as e:
        log.error('Failed to add prerouting rule: {}'.format(str(e)))
